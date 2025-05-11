import json
import logging
import os
import re
import select
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import IO, Callable, Optional

from planaieditor.tmpfilemanager import TempFileManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s"
)
lsp_handler_log = logging.getLogger("LSPHandler")  # For the main LSPHandler class


class LSPHandler:
    """
    Manages a Language Server Protocol (LSP) process, including starting,
    stopping, sending messages, and reading responses/stderr.
    """

    CONTENT_LENGTH_RE = re.compile(rb"^Content-Length: *(\d+)\r\n", re.IGNORECASE)

    def __init__(self, write_log: bool = False, log_dir: Path = Path("lsp_logs")):
        self.lsp_msg_lock: threading.Lock = threading.Lock()
        self.lsp_process: Optional[subprocess.Popen] = None
        self.lsp_stderr_reader: Optional[threading.Thread] = None
        self.lsp_stdout_reader_thread: Optional[threading.Thread] = None

        self.lsp_log_dir: Path = log_dir
        self.current_lsp_log_file: Optional[Path] = None
        self.lsp_log_lock: Optional[threading.Lock] = (
            threading.Lock() if write_log else None
        )
        self.write_log = write_log
        if write_log:
            self.lsp_log_dir.mkdir(parents=True, exist_ok=True)
            lsp_handler_log.info(
                f"LSP log directory set to: {self.lsp_log_dir.resolve()}"
            )

        self.temp_file_manager = TempFileManager()
        self.client_sid: Optional[str] = None
        self.client_socketio_emit: Optional[Callable] = None

        lsp_handler_log.info("LSPHandler instance created with TempFileManager.")

    def _rotate_lsp_log_file(self):
        """Generates a new log file name and sets it as the current log file."""
        if not self.write_log:
            return

        self.lsp_log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        new_log_file_name = f"lsp_messages_{timestamp}.jsonl"
        self.current_lsp_log_file = self.lsp_log_dir / new_log_file_name
        lsp_handler_log.info(
            f"LSP message logging will be written to: {self.current_lsp_log_file}"
        )

    def _log_to_jsonl_file(self, data: dict, log_type: str):
        """Appends a JSON log entry to the current LSP log file."""
        if not self.current_lsp_log_file:
            return
        log_entry = {"timestamp": time.time(), "type": log_type, "payload": data}
        try:
            with self.lsp_log_lock:
                with open(self.current_lsp_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            lsp_handler_log.error(
                f"Failed to write to LSP JSONL log file {self.current_lsp_log_file}: {e}",
                exc_info=True,
            )

    def _format_lsp_message(self, data: dict) -> bytes:
        """Formats a dictionary into a JSON-RPC message with LSP headers."""
        try:
            json_payload = json.dumps(data).encode("utf-8")
            content_length = len(json_payload)
            header = f"Content-Length: {content_length}\r\n\r\n".encode("utf-8")
            return header + json_payload
        except Exception as e:
            lsp_handler_log.error(f"Error formatting LSP message: {e}", exc_info=True)
            return b""

    def _read_one_lsp_message(
        self, stream: IO[bytes], timeout: float = 2.0
    ) -> Optional[dict]:
        """Reads a single LSP message from the stream (stdout) with timeout."""
        if not self.lsp_process:
            lsp_handler_log.warning(
                "Attempted to read message but LSP process is not active."
            )
            return None

        ready_to_read, _, _ = select.select([stream], [], [], timeout)
        if not ready_to_read:
            return None

        try:
            content_length = -1
            header_start_time = time.time()
            header_buffer = b""

            while True:  # Reading headers
                time_elapsed = time.time() - header_start_time
                if time_elapsed >= timeout:
                    lsp_handler_log.info(
                        f"Timeout reading LSP headers after {timeout} seconds."
                    )
                    if header_buffer:
                        lsp_handler_log.debug(
                            f"Header buffer at timeout: {header_buffer.decode(errors='ignore')}"
                        )
                    return None

                remaining_timeout = timeout - time_elapsed
                ready, _, _ = select.select(
                    [stream],
                    [],
                    [],
                    max(0, remaining_timeout / 2 if remaining_timeout > 0.2 else 0.1),
                )  # smaller non-blocking for char
                if not ready:
                    if (
                        not self.lsp_process or self.lsp_process.poll() is not None
                    ):  # process died
                        lsp_handler_log.info(
                            "LSP process ended while waiting for header data."
                        )
                        return None
                    continue  # continue to check main timeout

                try:
                    char = stream.read(1)
                    if not char:
                        lsp_handler_log.info(
                            "LSP stdout stream ended while reading headers (EOF)."
                        )
                        return None
                    header_buffer += char
                except (BlockingIOError, InterruptedError):
                    continue
                except Exception as e:
                    lsp_handler_log.error(
                        f"Exception reading header char: {e}", exc_info=True
                    )
                    return None

                if header_buffer.endswith(b"\r\n\r\n"):
                    break
                if content_length == -1:  # Parse on the fly
                    match = self.CONTENT_LENGTH_RE.search(header_buffer)
                    if match:
                        content_length = int(match.group(1))

            if content_length == -1:  # Final check if not found during loop
                match = self.CONTENT_LENGTH_RE.search(header_buffer)
                if match:
                    content_length = int(match.group(1))
                else:
                    lsp_handler_log.warning(
                        f"Did not find Content-Length. Headers: {header_buffer.decode(errors='ignore')}"
                    )
                    return None

            lsp_handler_log.debug(f"Received headers. Content-Length: {content_length}")

            # Reading body
            body_buffer = b""
            bytes_to_read = content_length
            body_start_time = time.time()
            time_elapsed_headers = (
                time.time() - header_start_time
            )  # time spent on headers
            remaining_body_timeout = timeout - time_elapsed_headers

            while len(body_buffer) < content_length:
                time_elapsed_body = time.time() - body_start_time
                if time_elapsed_body >= remaining_body_timeout:
                    lsp_handler_log.info(
                        f"Timeout reading LSP body. Read {len(body_buffer)}/{content_length}"
                    )
                    return None

                current_remaining_timeout = remaining_body_timeout - time_elapsed_body
                ready, _, _ = select.select(
                    [stream],
                    [],
                    [],
                    max(
                        0,
                        (
                            current_remaining_timeout / 2
                            if current_remaining_timeout > 0.2
                            else 0.1
                        ),
                    ),
                )
                if not ready:
                    if not self.lsp_process or self.lsp_process.poll() is not None:
                        lsp_handler_log.info(
                            "LSP process ended while waiting for body data."
                        )
                        return None
                    continue

                try:
                    chunk = stream.read(min(bytes_to_read - len(body_buffer), 4096))
                    if not chunk:
                        lsp_handler_log.error(
                            f"LSP stream ended prematurely reading body. Got {len(body_buffer)}/{content_length}."
                        )
                        return None
                    body_buffer += chunk
                except (BlockingIOError, InterruptedError):
                    continue
                except Exception as e:
                    lsp_handler_log.error(
                        f"Exception reading body chunk: {e}", exc_info=True
                    )
                    return None

            payload_str = body_buffer.decode("utf-8")
            original_payload = json.loads(payload_str)
            lsp_handler_log.debug(
                f"Received raw LSP Message: ID={original_payload.get('id')}, Method={original_payload.get('method')}"
            )

            # Translate URIs in the received message
            translated_payload = self.temp_file_manager.translate_message_to_client(
                original_payload
            )

            return translated_payload

        except json.JSONDecodeError as e:
            lsp_handler_log.error(
                f"Failed to decode LSP JSON payload: {e}. Payload: {body_buffer.decode('utf-8', errors='ignore') if 'body_buffer' in locals() else 'N/A'}",
                exc_info=True,
            )
        except EOFError as e:
            lsp_handler_log.info(f"LSP stream ended expectedly: {e}")
        except BrokenPipeError:
            lsp_handler_log.info("LSP process stdout pipe broke.")
        except Exception as e:
            if self.lsp_process and self.lsp_process.poll() is None:
                lsp_handler_log.error(
                    f"Unexpected error reading LSP stdout: {e}", exc_info=True
                )
            else:
                lsp_handler_log.info(
                    f"Error reading LSP stdout after process termination: {e}"
                )
        return None

    def _read_stderr(self, stream: IO[bytes]):
        """Reads stderr from the LSP process for logging."""
        try:
            while self.lsp_process and not stream.closed:
                # If self.lsp_process changes, this thread continues for the old proc until it ends.
                ready_to_read, _, _ = select.select([stream], [], [], 0.5)
                if not ready_to_read:
                    current_process = self.lsp_process  # Sample self.lsp_process
                    if not current_process or current_process.stderr != stream:
                        # Process changed or stream invalid
                        lsp_handler_log.info(
                            "LSP stderr reader: process changed or stream invalid. Exiting."
                        )
                        break
                    if current_process.poll() is not None:  # Process died
                        lsp_handler_log.info(
                            "LSP stderr reader: process died. Exiting."
                        )
                        break
                    continue

                # Read all available lines
                lines_output = []
                while select.select([stream], [], [], 0)[
                    0
                ]:  # Non-blocking check for more
                    line_bytes = stream.readline()
                    if not line_bytes:  # Stream ended
                        lsp_handler_log.debug("LSP stderr stream ended during read.")
                        return  # Exit thread
                    lines_output.append(
                        line_bytes.decode("utf-8", errors="ignore").strip()
                    )

                if lines_output:
                    lsp_handler_log.info(
                        f"LSP stderr output:\n{os.linesep.join(lines_output)}"
                    )

            lsp_handler_log.info("LSP stderr stream processing stopped.")
        except Exception as e:
            if self.lsp_process:
                lsp_handler_log.error(f"Error reading LSP stderr: {e}", exc_info=True)
            else:
                lsp_handler_log.info(
                    f"Error reading LSP stderr after process termination: {e}"
                )
        finally:
            lsp_handler_log.info("LSP stderr reader thread finished.")

    def _read_stdout_loop(
        self,
        stdout_stream: IO[bytes],
        associated_proc: subprocess.Popen,
        sid: str,
        socketio_emit_func: Callable,
    ):
        """Reads LSP messages from stdout in a loop and dispatches them."""
        lsp_handler_log.info(
            f"LSP stdout reader thread started for SID {sid}, PID {associated_proc.pid}."
        )
        try:
            while (
                self.lsp_process == associated_proc
                and associated_proc.poll() is None
                and not stdout_stream.closed
            ):

                response = self._read_one_lsp_message(stdout_stream, timeout=1.0)

                if response is not None:
                    lsp_handler_log.info(
                        f"LSP message from server (for SID {sid}, PID {associated_proc.pid}): ID={response.get('id')}, Method={response.get('method')}"
                    )
                    # Response is already translated by _read_one_lsp_message
                    self._log_to_jsonl_file(response, "response_from_server")
                    socketio_emit_func("lsp_response", response, room=sid)
                elif not (
                    self.lsp_process == associated_proc
                    and associated_proc.poll() is None
                ):
                    lsp_handler_log.info(
                        f"LSP process {associated_proc.pid} (for SID {sid}) changed or ended. Stdout reader stopping."
                    )
                    break
                # If response is None (timeout) and process is still the same and alive, continue loop.

        except BrokenPipeError:
            lsp_handler_log.info(
                f"LSP stdout pipe broke for SID {sid}, PID {associated_proc.pid}. Reader thread stopping."
            )
        except Exception as e:
            if self.lsp_process == associated_proc and associated_proc.poll() is None:
                lsp_handler_log.error(
                    f"Exception in LSP stdout reader loop for SID {sid}, PID {associated_proc.pid}: {e}",
                    exc_info=True,
                )
            else:
                lsp_handler_log.info(
                    f"LSP stdout reader loop for SID {sid}, PID {associated_proc.pid} exiting due to process stop or change: {e}"
                )
        finally:
            lsp_handler_log.info(
                f"LSP stdout reader thread finished for SID {sid}, PID {associated_proc.pid}."
            )

    def start_lsp_process(
        self, python_executable: str, sid: str, socketio_emit: Callable
    ) -> bool:
        """Starts the jedi-language-server subprocess."""
        with self.lsp_msg_lock:
            if self.lsp_process:
                lsp_handler_log.warning(
                    "LSP process already running. Stopping it first."
                )
                self._stop_lsp_process_internal()

            self._rotate_lsp_log_file()
            # Re-initialize TempFileManager for a fresh session
            self.temp_file_manager = TempFileManager()

            # Store current client info
            self.client_sid = sid
            self.client_socketio_emit = socketio_emit

            jedi_path_str = str(Path(python_executable).parent / "jedi-language-server")
            lsp_handler_log.info(
                f"Starting LSP process using: {jedi_path_str} for SID: {sid}"
            )
            try:
                cmd = [jedi_path_str]
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0,
                )
                self.lsp_process = proc

                self.lsp_stderr_reader = threading.Thread(
                    target=self._read_stderr, args=(proc.stderr,), daemon=True
                )
                self.lsp_stderr_reader.start()

                self.lsp_stdout_reader_thread = threading.Thread(
                    target=self._read_stdout_loop,
                    args=(
                        proc.stdout,
                        proc,
                        self.client_sid,
                        self.client_socketio_emit,
                    ),
                    daemon=True,
                )
                self.lsp_stdout_reader_thread.start()

                lsp_handler_log.info(
                    f"LSP process started (PID: {proc.pid}) for SID {sid}. Stderr and stdout readers running."
                )
                return True
            except FileNotFoundError:
                lsp_handler_log.error(
                    f"Jedi-language-server executable not found: {jedi_path_str}"
                )
                # self.lsp_process is None here, _cleanup_lsp_resources will handle client_sid etc.
                self._cleanup_lsp_resources()
                return False
            except Exception as e:
                lsp_handler_log.error(
                    f"Failed to start LSP process for SID {sid}: {e}", exc_info=True
                )
                if (
                    self.lsp_process
                ):  # If proc was partially created and assigned to self.lsp_process
                    self._stop_lsp_process_internal()
                else:  # if self.lsp_process was never assigned
                    self._cleanup_lsp_resources()
                return False

    def _cleanup_lsp_resources(self):
        """Internal helper to clear LSP resources."""
        self.lsp_process = None
        self.lsp_stderr_reader = None
        self.lsp_stdout_reader_thread = None  # Clear new thread reference
        self.client_sid = None  # Clear client info
        self.client_socketio_emit = None
        lsp_handler_log.debug(
            "LSP process, reader threads, and client info references cleared."
        )

    def _stop_lsp_process_internal(self):
        """Stops the LSP process without acquiring the lock (for internal use)."""
        proc_to_stop = self.lsp_process  # Capture the process to stop

        if not proc_to_stop:
            lsp_handler_log.info(
                "No active LSP process found to stop by _stop_lsp_process_internal."
            )
            self._cleanup_lsp_resources()  # Ensure resources are clear if called when no proc
            return

        current_pid = proc_to_stop.pid
        lsp_handler_log.info(f"Stopping LSP process (PID: {current_pid}).")

        # Important: Signal threads that this specific process instance is ending.
        # Do this by setting self.lsp_process to None if proc_to_stop is the current one.
        # This must happen before joining, so threads see the change.
        if self.lsp_process == proc_to_stop:
            self.lsp_process = None

        try:
            if proc_to_stop.stdin and not proc_to_stop.stdin.closed:
                proc_to_stop.stdin.close()
        except OSError as e:
            lsp_handler_log.warning(
                f"Error closing LSP stdin for PID {current_pid}: {e}"
            )

        try:
            proc_to_stop.terminate()
            proc_to_stop.wait(timeout=2)  # Use proc_to_stop
            lsp_handler_log.info(
                f"LSP process (PID: {current_pid}) terminated gracefully."
            )
        except subprocess.TimeoutExpired:
            lsp_handler_log.warning(
                f"LSP process (PID: {current_pid}) did not terminate gracefully, killing."
            )
            proc_to_stop.kill()
            proc_to_stop.wait(timeout=1)  # Use proc_to_stop
            lsp_handler_log.info(f"LSP process (PID: {current_pid}) killed.")
        except Exception as e:
            lsp_handler_log.error(
                f"Error stopping LSP process (PID: {current_pid}): {e}",
                exc_info=True,
            )

        stdout_thread_ref = self.lsp_stdout_reader_thread
        stderr_thread_ref = self.lsp_stderr_reader

        if stdout_thread_ref and stdout_thread_ref.is_alive():
            lsp_handler_log.debug(
                f"Waiting for stdout reader thread (for PID {current_pid}) to join..."
            )
            stdout_thread_ref.join(timeout=1.0)
            if stdout_thread_ref.is_alive():
                lsp_handler_log.warning(
                    f"Stdout reader thread (for PID {current_pid}) did not join in time."
                )

        if stderr_thread_ref and stderr_thread_ref.is_alive():
            lsp_handler_log.debug(
                f"Waiting for stderr reader thread (for PID {current_pid}) to join..."
            )
            stderr_thread_ref.join(timeout=1.0)
            if stderr_thread_ref.is_alive():
                lsp_handler_log.warning(
                    f"Stderr reader thread (for PID {current_pid}) did not join in time."
                )

        self._cleanup_lsp_resources()

        self.temp_file_manager.cleanup_all_temp_files()
        lsp_handler_log.info(
            f"LSP process stop sequence for PID {current_pid} complete, temporary files cleaned up."
        )

    def stop_lsp_process(self):
        """Stops the jedi-language-server subprocess and cleans up resources."""
        with self.lsp_msg_lock:  # Acquire lock here
            self._stop_lsp_process_internal()

    def send_lsp_message(self, message: dict):  # SID and socketio_emit removed
        """Sends a message to the LSP process."""
        lsp_handler_log.debug(
            f"send_lsp_message called (current client SID: {self.client_sid}): Method={message.get('method')}, ID={message.get('id')}"
        )

        try:
            message_to_translate = json.loads(json.dumps(message))  # Deep copy
            translated_message_for_server = (
                self.temp_file_manager.translate_message_to_server(message_to_translate)
            )
        except Exception as e:
            lsp_handler_log.error(
                f"Error during URI translation for server-bound message (SID: {self.client_sid}): {e}",
                exc_info=True,
            )
            lsp_handler_log.error("Sending original message due to translation error.")
            translated_message_for_server = message

        if json.dumps(message) != json.dumps(translated_message_for_server):
            lsp_handler_log.info(
                f"Client->Server URI Translation Occurred (SID: {self.client_sid})."
            )
            lsp_handler_log.debug(
                f"LSP message for server (SID: {self.client_sid}, post-translation): {json.dumps(translated_message_for_server, indent=2)}"
            )

        self._log_to_jsonl_file(translated_message_for_server, "request_to_server")

        formatted_message_bytes = self._format_lsp_message(
            translated_message_for_server
        )
        if not formatted_message_bytes:
            lsp_handler_log.error(
                f"Failed to format translated message (SID: {self.client_sid}), not sending."
            )
            return

        try:
            with self.lsp_msg_lock:
                # Capture current state under lock
                current_proc = self.lsp_process
                current_sid_context = self.client_sid

                if (
                    not current_proc
                    or not current_proc.stdin
                    or current_proc.stdin.closed
                ):
                    lsp_handler_log.warning(
                        f"LSP process became inactive or stdin closed before writing (intended for SID: {current_sid_context}). Msg: {message.get('method')}"
                    )
                    return

                lsp_handler_log.info(
                    f"Preparing to send raw LSP message (for SID: {current_sid_context}): Method={message.get('method')}, ID={message.get('id')}"
                )

                current_proc.stdin.write(formatted_message_bytes)
                current_proc.stdin.flush()
                lsp_handler_log.debug(
                    f"LSP message sent (for SID: {current_sid_context}): {message.get('method')}"
                )

        except BrokenPipeError:
            lsp_handler_log.error(
                f"LSP stdin pipe broke (SID context: {self.client_sid}). Process likely died.",
                exc_info=True,
            )
            self.stop_lsp_process()  # This will acquire its own lock
        except Exception as e:
            lsp_handler_log.error(
                f"Error writing to LSP stdin or during lock (SID context: {self.client_sid}): {e}",
                exc_info=True,
            )


# --- Global Instance of LSPHandler ---
lsp_handler_instance = LSPHandler()

# --- Main execution / Example Usage ---
if __name__ == "__main__":
    python_exe = "python"  # Adjust if jedi-language-server is not in PATH
    # or use /path/to/your/venv/bin/python

    def mock_emit_main(event, data, room):
        lsp_handler_log.info(
            f"MOCK EMIT Event: {event}, SID: {room}, Data: {json.dumps(data, indent=2)}"
        )

    if not lsp_handler_instance.start_lsp_process(
        python_exe, "main_test_session_456", mock_emit_main
    ):
        lsp_handler_log.error("Failed to start LSP, exiting example.")
        exit()

    def mock_emit_main(event, data, room):  # Renamed to avoid conflict if imported
        lsp_handler_log.info(
            f"MOCK EMIT Event: {event}, SID: {room}, Data: {json.dumps(data, indent=2)}"
        )

    sid_main_example = "main_test_session_456"

    init_msg = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "processId": None,
            "clientInfo": {"name": "MainTestClient", "version": "1.0"},
            "rootUri": Path(os.getcwd()).as_uri(),
            "capabilities": {},
            "trace": "verbose",
            "workspaceFolders": [
                {"uri": Path(os.getcwd()).as_uri(), "name": "workspace"}
            ],
        },
    }
    lsp_handler_instance.send_lsp_message(init_msg)
    time.sleep(
        2
    )  # Allow time for server to respond to initialize and for stdout reader to process

    initialized_msg = {"jsonrpc": "2.0", "method": "initialized", "params": {}}
    lsp_handler_instance.send_lsp_message(initialized_msg)
    time.sleep(0.5)

    did_open_msg = {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": "inmemory://project/file1.py",
                "languageId": "python",
                "version": 1,
                "text": "import os\n\ndef main_func():\n    print(os.getpid())\n    # A comment for action\n",
            }
        },
    }
    lsp_handler_instance.send_lsp_message(did_open_msg)
    time.sleep(0.5)

    code_action_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "textDocument/codeAction",
        "params": {
            "textDocument": {"uri": "inmemory://project/file1.py"},
            "range": {
                "start": {"line": 3, "character": 7},
                "end": {"line": 3, "character": 7},
            },  # After "# A "
            "context": {"diagnostics": []},
        },
    }
    lsp_handler_instance.send_lsp_message(code_action_msg)
    time.sleep(3)  # Allow more time for code action and response processing

    did_close_msg = {
        "jsonrpc": "2.0",
        "method": "textDocument/didClose",
        "params": {"textDocument": {"uri": "inmemory://project/file1.py"}},
    }
    lsp_handler_instance.send_lsp_message(did_close_msg)
    time.sleep(0.5)

    shutdown_msg = {"jsonrpc": "2.0", "id": 100, "method": "shutdown"}
    lsp_handler_instance.send_lsp_message(shutdown_msg)
    time.sleep(1)

    exit_msg = {"jsonrpc": "2.0", "method": "exit"}
    lsp_handler_instance.send_lsp_message(exit_msg)
    time.sleep(1)  # Give it a moment before forced stop if exit doesn't kill it

    lsp_handler_instance.stop_lsp_process()
    lsp_handler_log.info("LSP Handler example finished.")
