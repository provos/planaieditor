import json
import logging
import re  # Import regex for header parsing
import select
import subprocess
import threading
import time
from pathlib import Path
from typing import IO, Callable, Optional

# Configure basic logging for the LSP handler
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s"
)
# Use a logger specific to this module/class for better context
log = logging.getLogger("LSPHandler")


class LSPHandler:
    """
    Manages a Language Server Protocol (LSP) process, including starting,
    stopping, sending messages, and reading responses/stderr.
    """

    CONTENT_LENGTH_RE = re.compile(rb"^Content-Length: *(\d+)\r\n", re.IGNORECASE)

    def __init__(self):
        self.lsp_write_lock: Optional[threading.Lock] = threading.Lock()
        self.lsp_process: Optional[subprocess.Popen] = None
        self.lsp_stderr_reader: Optional[threading.Thread] = None
        log.info("LSPHandler instance created.")

    def _format_lsp_message(self, data: dict) -> bytes:
        """Formats a dictionary into a JSON-RPC message with LSP headers."""
        try:
            json_payload = json.dumps(data).encode("utf-8")
            content_length = len(json_payload)
            header = f"Content-Length: {content_length}\r\n\r\n".encode("utf-8")
            return header + json_payload
        except Exception as e:
            log.error(f"Error formatting LSP message: {e}", exc_info=True)
            return b""

    def _read_one_lsp_message(
        self, stream: IO[bytes], timeout: float = 2.0
    ) -> Optional[dict]:
        """Reads a single LSP message from the stream (stdout) with timeout."""
        if not self.lsp_process:  # Ensure process is still meant to be active
            log.warning("Attempted to read message but LSP process is not active.")
            return None

        # Use select to check if there's data to be read with timeout
        ready_to_read, _, _ = select.select([stream], [], [], timeout)
        if not ready_to_read:
            log.info(f"Timeout waiting for LSP response after {timeout} seconds")
            return None

        try:
            content_length = -1
            header_start_time = time.time()
            while True:
                if time.time() - header_start_time > timeout:
                    log.info(f"Timeout reading LSP headers after {timeout} seconds")
                    return None

                if not select.select(
                    [stream], [], [], timeout - (time.time() - header_start_time)
                )[0]:
                    log.info("Timeout waiting for next header line")
                    return None

                header_line = stream.readline()
                if not header_line:
                    log.info("LSP stdout stream ended while reading headers.")
                    return None

                if header_line == b"\r\n":
                    break

                match = self.CONTENT_LENGTH_RE.match(header_line)
                if match:
                    content_length = int(match.group(1))

            if content_length == -1:
                log.warning("Did not find Content-Length header before blank line.")
                return None

            body_read_timeout = timeout - (time.time() - header_start_time)
            if body_read_timeout <= 0:
                log.info("No time left to read LSP message body.")
                return None

            if not select.select([stream], [], [], body_read_timeout)[0]:
                log.info("Timeout waiting for message body after headers")
                return None

            body = stream.read(content_length)
            if len(body) < content_length:
                log.error(
                    f"LSP stdout stream ended prematurely while reading body. "
                    f"Expected {content_length}, got {len(body)}."
                )
                return None

            try:
                payload = json.loads(body.decode("utf-8"))
                log.debug(
                    f"Received LSP Message: {payload.get('method', payload.get('id', ''))}"
                )
                return payload
            except json.JSONDecodeError as e:
                log.error(
                    f"Failed to decode LSP JSON payload: {e}. Payload: {body.decode('utf-8', errors='ignore')}",
                    exc_info=True,
                )
                return None
        except EOFError as e:
            log.info(f"LSP stream ended expectedly: {e}")
        except BrokenPipeError:
            log.info("LSP process stdout pipe broke (likely process termination).")
        except Exception as e:
            if self.lsp_process:  # Check if process termination was intended
                log.error(f"Unexpected error reading LSP stdout: {e}", exc_info=True)
            else:
                log.info(f"Error reading LSP stdout after process termination: {e}")
        return None

    def _read_stderr(self, stream: IO[bytes]):
        """Reads stderr from the LSP process for logging."""
        try:
            while (
                self.lsp_process and not stream.closed
            ):  # Continue as long as process exists and stream is open
                # Use select to check if there's data to read (timeout of 0.5 seconds)
                ready_to_read, _, _ = select.select([stream], [], [], 0.5)
                if not ready_to_read:
                    # No data available, continue and check again, also check if lsp_process is still valid
                    if not self.lsp_process:
                        break
                    continue

                stderr_lines = []
                while select.select([stream], [], [], 0)[
                    0
                ]:  # Non-blocking check for more lines
                    line = stream.readline()
                    if not line:
                        log.debug("LSP stderr stream ended.")
                        return  # Exit the function if stream has ended

                    stderr_lines.append(line.decode("utf-8", errors="ignore").strip())

                if stderr_lines:
                    stderr_block = "\n".join(stderr_lines)
                    log.info(f"LSP stderr output:\n{stderr_block}")
            log.info(
                "LSP stderr stream processing stopped (stream closed or process ended)."
            )

        except Exception as e:
            # Check if process still exists before logging error
            if self.lsp_process:
                log.error(f"Error reading LSP stderr: {e}", exc_info=True)
            else:
                log.info(f"Error reading LSP stderr after process termination: {e}")
        finally:
            log.info("LSP stderr reader thread finished.")

    def start_lsp_process(self, python_executable: str) -> bool:
        """Starts the jedi-language-server subprocess."""
        if self.lsp_process:
            log.warning("LSP process already running. Stopping it first.")
            self.stop_lsp_process()

        jedi_path = Path(python_executable).parent / "jedi-language-server"
        log.info(f"Starting LSP process using: {jedi_path}")
        try:
            cmd = [str(jedi_path)]  # Ensure jedi_path is a string
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,  # Important for unbuffered I/O
            )
            self.lsp_process = proc

            stderr_thread = threading.Thread(
                target=self._read_stderr, args=(proc.stderr,), daemon=True
            )
            self.lsp_stderr_reader = stderr_thread
            stderr_thread.start()

            log.info(
                f"LSP process started (PID: {proc.pid}). Stderr reader thread running."
            )
            return True

        except FileNotFoundError:
            log.error(f"Jedi-language-server executable not found: {jedi_path}")
            self.lsp_process = None  # Ensure lsp_process is None if start fails
            return False
        except Exception as e:
            log.error(f"Failed to start LSP process: {e}", exc_info=True)
            if self.lsp_process:  # If proc was partially created
                self._stop_lsp_process_internal()  # Attempt cleanup
            self.lsp_process = None  # Ensure lsp_process is None if start fails
            return False

    def _cleanup_lsp_resources(self):
        """Internal helper to clear LSP resources."""
        self.lsp_process = None
        self.lsp_stderr_reader = (
            None  # The thread itself will exit, just clear reference
        )
        log.debug("LSP resources cleaned up.")

    def _stop_lsp_process_internal(self):
        """Stops the LSP process without acquiring the lock (for internal use)."""
        proc = self.lsp_process
        if proc:
            log.info(f"Stopping LSP process (PID: {proc.pid}).")
            # Set self.lsp_process to None early to signal other parts (like _read_stderr)
            # that the process is being shut down.
            current_pid = proc.pid
            self.lsp_process = None  # Signal intent to stop

            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
            except OSError as e:
                log.warning(f"Error closing LSP stdin for PID {current_pid}: {e}")

            try:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                    log.info(f"LSP process (PID: {current_pid}) terminated gracefully.")
                except subprocess.TimeoutExpired:
                    log.warning(
                        f"LSP process (PID: {current_pid}) did not terminate gracefully, killing."
                    )
                    proc.kill()
                    proc.wait(timeout=1)
                    log.info(f"LSP process (PID: {current_pid}) killed.")
            except Exception as e:
                log.error(
                    f"Error stopping LSP process (PID: {current_pid}): {e}",
                    exc_info=True,
                )
            finally:
                # Ensure resources are removed even if stopping fails
                self._cleanup_lsp_resources()  # This will clear self.lsp_process, etc.
        else:
            log.info("No active LSP process found to stop.")
            self._cleanup_lsp_resources()  # Ensure cleanup if called redundantly

        stderr_thread = self.lsp_stderr_reader  # Get local copy before cleanup
        if stderr_thread and stderr_thread.is_alive():
            log.debug("Waiting for stderr reader thread to join...")
            stderr_thread.join(timeout=1.0)
            if stderr_thread.is_alive():
                log.warning("Stderr reader thread did not join in time.")
        self.lsp_stderr_reader = None  # Ensure it's cleared after attempting join

        log.info("LSP process and related resources stop sequence complete.")

    def stop_lsp_process(self):
        """Stops the jedi-language-server subprocess and cleans up resources."""
        self._stop_lsp_process_internal()

    def send_lsp_message(self, sid: str, message: dict, socketio_emit: Callable):
        """Sends a message to the LSP process and handles the response or notification."""
        log.info(
            f"Preparing to send LSP message (SID: {sid}): Method: {message.get('method')}, ID: {message.get('id')}"
        )
        # log.info(f"LSP message details: {json.dumps(message, indent=2)}") # Can be verbose

        if (
            not self.lsp_process
            or not self.lsp_process.stdin
            or self.lsp_process.stdin.closed
        ):
            log.warning(
                f"Cannot send LSP message (SID: {sid}): LSP process not active or stdin closed."
            )
            return

        formatted_message = self._format_lsp_message(message)
        if not formatted_message:
            log.error(
                f"Failed to format message (SID: {sid}), not sending: {message.get('method')}"
            )
            return

        try:
            with self.lsp_write_lock:
                if (
                    not self.lsp_process
                    or not self.lsp_process.stdin
                    or self.lsp_process.stdin.closed
                ):
                    log.warning(
                        f"LSP process became inactive or stdin closed before writing (SID: {sid})."
                    )
                    return
                self.lsp_process.stdin.write(formatted_message)
                self.lsp_process.stdin.flush()
                log.debug(f"LSP message sent (SID: {sid}): {message.get('method')}")

                expects_response = "id" in message
                if expects_response:
                    if not self.lsp_process or not self.lsp_process.stdout:
                        log.warning(
                            f"LSP process or stdout not available for response (SID: {sid})."
                        )
                        return
                    # Read the response synchronously with timeout
                    response = self._read_one_lsp_message(
                        self.lsp_process.stdout, timeout=10.0
                    )  # Increased timeout
                    if response:
                        log.info(
                            f"LSP response received for ID {response.get('id')} (SID: {sid})"
                        )
                        socketio_emit("lsp_response", response, room=sid)
                    else:
                        log.warning(
                            f"No response or error reading response for message with id: {message.get('id')} (SID: {sid})"
                        )
                else:
                    log.debug(
                        f"Message (SID: {sid}, Method: {message.get('method')}) is a notification, not waiting for response."
                    )

        except BrokenPipeError:
            log.error(
                f"LSP process stdin pipe broke while writing (SID: {sid}). Process likely died."
            )
            self.stop_lsp_process()  # Trigger cleanup
        except Exception as e:
            log.error(
                f"Error writing to LSP stdin or reading response (SID: {sid}): {e}",
                exc_info=True,
            )


# --- Global Instance of LSPHandler ---
lsp_handler_instance = LSPHandler()
