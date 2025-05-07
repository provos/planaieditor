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
        self.lsp_msg_lock: Optional[threading.Lock] = threading.Lock()
        self.lsp_process: Optional[subprocess.Popen] = None
        self.lsp_stderr_reader: Optional[threading.Thread] = None
        self.lsp_log_dir: Path = log_dir
        self.current_lsp_log_file: Optional[Path] = None
        self.lsp_log_lock: threading.Lock = threading.Lock() if write_log else None
        self.write_log = write_log
        if write_log:
            self.lsp_log_dir.mkdir(parents=True, exist_ok=True)
            lsp_handler_log.info(
                f"LSP log directory set to: {self.lsp_log_dir.resolve()}"
            )

        self.temp_file_manager = TempFileManager()

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
            lsp_handler_log.info(
                f"Timeout waiting for LSP response after {timeout} seconds (select)"
            )
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
                ready_to_read, _, _ = select.select([stream], [], [], 0.5)
                if not ready_to_read:
                    if not self.lsp_process:
                        break  # Process has been stopped
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

    def start_lsp_process(self, python_executable: str) -> bool:
        """Starts the jedi-language-server subprocess."""
        # all of this happens under the write lock, so that all attempted send_lsp_message calls
        # will wait until the new server is started
        with self.lsp_msg_lock:
            if self.lsp_process:
                lsp_handler_log.warning(
                    "LSP process already running. Stopping it first."
                )
                self.stop_lsp_process()

            self._rotate_lsp_log_file()
            # Re-initialize TempFileManager for a fresh session
            self.temp_file_manager = TempFileManager()

            jedi_path_str = str(Path(python_executable).parent / "jedi-language-server")
            lsp_handler_log.info(f"Starting LSP process using: {jedi_path_str}")
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
                lsp_handler_log.info(
                    f"LSP process started (PID: {proc.pid}). Stderr reader running."
                )
                return True
            except FileNotFoundError:
                lsp_handler_log.error(
                    f"Jedi-language-server executable not found: {jedi_path_str}"
                )
                self.lsp_process = None
                return False
            except Exception as e:
                lsp_handler_log.error(
                    f"Failed to start LSP process: {e}", exc_info=True
                )
                if self.lsp_process:
                    self._stop_lsp_process_internal()
                self.lsp_process = None
                return False

    def _cleanup_lsp_resources(self):
        """Internal helper to clear LSP resources."""
        self.lsp_process = None
        self.lsp_stderr_reader = None  # Thread will exit on its own
        lsp_handler_log.debug("LSP process and stderr_reader references cleared.")

    def _stop_lsp_process_internal(self):
        """Stops the LSP process without acquiring the lock (for internal use)."""
        proc = self.lsp_process
        if proc:
            current_pid = proc.pid
            lsp_handler_log.info(f"Stopping LSP process (PID: {current_pid}).")
            self.lsp_process = None  # Signal intent to stop early

            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
            except OSError as e:
                lsp_handler_log.warning(
                    f"Error closing LSP stdin for PID {current_pid}: {e}"
                )
            try:
                proc.terminate()
                proc.wait(timeout=2)
                lsp_handler_log.info(
                    f"LSP process (PID: {current_pid}) terminated gracefully."
                )
            except subprocess.TimeoutExpired:
                lsp_handler_log.warning(
                    f"LSP process (PID: {current_pid}) did not terminate gracefully, killing."
                )
                proc.kill()
                proc.wait(timeout=1)
                lsp_handler_log.info(f"LSP process (PID: {current_pid}) killed.")
            except Exception as e:
                lsp_handler_log.error(
                    f"Error stopping LSP process (PID: {current_pid}): {e}",
                    exc_info=True,
                )
        else:
            lsp_handler_log.info("No active LSP process found to stop.")

        stderr_thread_ref = (
            self.lsp_stderr_reader
        )  # Local copy before it's cleared by _cleanup_lsp_resources

        self._cleanup_lsp_resources()  # Clear self.lsp_process, self.lsp_stderr_reader

        if stderr_thread_ref and stderr_thread_ref.is_alive():
            lsp_handler_log.debug("Waiting for stderr reader thread to join...")
            stderr_thread_ref.join(timeout=1.0)
            if stderr_thread_ref.is_alive():
                lsp_handler_log.warning("Stderr reader thread did not join in time.")

        self.temp_file_manager.cleanup_all_temp_files()
        lsp_handler_log.info(
            "LSP process and resources stop sequence complete, temporary files cleaned up."
        )

    def stop_lsp_process(self):
        """Stops the jedi-language-server subprocess and cleans up resources."""
        self._stop_lsp_process_internal()

    def send_lsp_message(self, sid: str, message: dict, socketio_emit: Callable):
        """Sends a message to the LSP process and handles the response or notification."""

        # Translate URIs in the message to be sent
        try:
            message_to_translate = json.loads(json.dumps(message))  # Deep copy
            translated_message_for_server = (
                self.temp_file_manager.translate_message_to_server(message_to_translate)
            )
        except Exception as e:
            lsp_handler_log.error(
                f"Error during URI translation for server-bound message (SID: {sid}): {e}",
                exc_info=True,
            )
            lsp_handler_log.error("Sending original message due to translation error.")
            translated_message_for_server = message  # Fallback

        if json.dumps(message) != json.dumps(translated_message_for_server):
            lsp_handler_log.info(
                f"Client->Server URI Translation Occurred (SID: {sid})."
            )
            lsp_handler_log.debug(
                f"LSP message for server (SID: {sid}, post-translation): {json.dumps(translated_message_for_server, indent=2)}"
            )

        # Log the (potentially translated) request to JSONL file
        self._log_to_jsonl_file(translated_message_for_server, "request_to_server")

        formatted_message_bytes = self._format_lsp_message(
            translated_message_for_server
        )
        if not formatted_message_bytes:
            lsp_handler_log.error(
                f"Failed to format translated message (SID: {sid}), not sending."
            )
            return

        try:
            with self.lsp_msg_lock:
                if (
                    not self.lsp_process
                    or not self.lsp_process.stdin
                    or self.lsp_process.stdin.closed
                ):
                    lsp_handler_log.warning(
                        f"LSP process became inactive or stdin closed before writing (SID: {sid})."
                    )
                    return
                lsp_handler_log.info(
                    f"Preparing to send raw LSP message (SID: {sid}): Method={message.get('method')}, ID={message.get('id')}"
                )

                self.lsp_process.stdin.write(formatted_message_bytes)
                self.lsp_process.stdin.flush()
                lsp_handler_log.debug(
                    f"LSP message sent (SID: {sid}): {translated_message_for_server.get('method')}"
                )

                # we seralize response reading on the same lock
                expects_response = "id" in message  # Check original message for 'id'
                if expects_response:
                    if not self.lsp_process or not self.lsp_process.stdout:
                        lsp_handler_log.warning(
                            f"LSP process or stdout not available for response (SID: {sid})."
                        )
                        return

                    response = self._read_one_lsp_message(
                        self.lsp_process.stdout, timeout=10.0
                    )
                    # response is already translated by _read_one_lsp_message
                    if response:
                        lsp_handler_log.info(
                            f"LSP response received for ID {response.get('id')} (SID: {sid})"
                        )
                        self._log_to_jsonl_file(
                            response, "response_from_server"
                        )  # Log translated response
                        socketio_emit("lsp_response", response, room=sid)
                    else:
                        lsp_handler_log.warning(
                            f"No response/error reading for msg ID: {message.get('id')} (SID: {sid})"
                        )
                        self._log_to_jsonl_file(
                            {
                                "id": message.get("id"),
                                "error": "No response or timeout from LSP server",
                            },
                            "response_error",
                        )
                else:
                    lsp_handler_log.debug(
                        f"Message (SID: {sid}, Method: {message.get('method')}) is a notification."
                    )

        except BrokenPipeError:
            lsp_handler_log.error(
                f"LSP stdin pipe broke (SID: {sid}). Process likely died.",
                exc_info=True,
            )
            self.stop_lsp_process()
        except Exception as e:
            lsp_handler_log.error(
                f"Error writing to LSP stdin or reading response (SID: {sid}): {e}",
                exc_info=True,
            )


# --- Global Instance of LSPHandler ---
lsp_handler_instance = LSPHandler()

# --- Main execution / Example Usage ---
if __name__ == "__main__":
    python_exe = "python"  # Adjust if jedi-language-server is not in PATH
    # or use /path/to/your/venv/bin/python

    if not lsp_handler_instance.start_lsp_process(python_exe):
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
    lsp_handler_instance.send_lsp_message(sid_main_example, init_msg, mock_emit_main)
    time.sleep(1)  # Allow time for server to respond to initialize

    initialized_msg = {"jsonrpc": "2.0", "method": "initialized", "params": {}}
    lsp_handler_instance.send_lsp_message(
        sid_main_example, initialized_msg, mock_emit_main
    )
    time.sleep(0.1)

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
    lsp_handler_instance.send_lsp_message(
        sid_main_example, did_open_msg, mock_emit_main
    )
    time.sleep(0.2)

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
    lsp_handler_instance.send_lsp_message(
        sid_main_example, code_action_msg, mock_emit_main
    )
    time.sleep(2)  # Allow more time for code action

    did_close_msg = {
        "jsonrpc": "2.0",
        "method": "textDocument/didClose",
        "params": {"textDocument": {"uri": "inmemory://project/file1.py"}},
    }
    lsp_handler_instance.send_lsp_message(
        sid_main_example, did_close_msg, mock_emit_main
    )
    time.sleep(0.1)

    shutdown_msg = {"jsonrpc": "2.0", "id": 100, "method": "shutdown"}
    lsp_handler_instance.send_lsp_message(
        sid_main_example, shutdown_msg, mock_emit_main
    )
    time.sleep(0.5)

    exit_msg = {"jsonrpc": "2.0", "method": "exit"}
    lsp_handler_instance.send_lsp_message(sid_main_example, exit_msg, mock_emit_main)
    time.sleep(0.5)  # Give it a moment before forced stop if exit doesn't kill it

    lsp_handler_instance.stop_lsp_process()
    lsp_handler_log.info("LSP Handler example finished.")
