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
    level=logging.INFO, format="%(asctime)s - %(levelname)s - [LSPHandler] %(message)s"
)
log = logging.getLogger(__name__)

# --- Global Dictionaries to Manage LSP Subprocesses ---
lsp_process: Optional[subprocess.Popen] = None
lsp_stderr_reader: Optional[threading.Thread] = None
lsp_write_lock: Optional[threading.Lock] = None

# Regex to find Content-Length header
CONTENT_LENGTH_RE = re.compile(rb"^Content-Length: *(\d+)\r\n", re.IGNORECASE)

# --- LSP Message Framing Helper ---


def _format_lsp_message(data: dict) -> bytes:
    """Formats a dictionary into a JSON-RPC message with LSP headers."""
    try:
        json_payload = json.dumps(data).encode("utf-8")
        content_length = len(json_payload)
        header = f"Content-Length: {content_length}\r\n\r\n".encode("utf-8")
        return header + json_payload
    except Exception as e:
        log.error(f"Error formatting LSP message: {e}", exc_info=True)
        # Return an empty byte string or raise an exception depending on desired handling
        return b""


# --- Helper to read a single LSP message ---
def _read_one_lsp_message(stream: IO[bytes], timeout: float = 2.0) -> Optional[dict]:
    """Reads a single LSP message from the stream (stdout) with timeout.

    Args:
        stream: The stdout stream from the LSP process
        timeout: Maximum time in seconds to wait for a response

    Returns:
        The parsed JSON response or None if no response or timeout
    """
    # Use select to check if there's data to be read with timeout
    if not select.select([stream], [], [], timeout)[0]:
        log.info(f"Timeout waiting for LSP response after {timeout} seconds")
        return None

    try:
        content_length = -1
        # Read header lines until a blank line is encountered
        header_start_time = time.time()
        while True:
            # Check if we've exceeded the timeout for headers
            if time.time() - header_start_time > timeout:
                log.info(f"Timeout reading LSP headers after {timeout} seconds")
                return None

            # Check if there's data available before reading
            if not select.select([stream], [], [], timeout)[0]:
                log.info("Timeout waiting for next header line")
                return None

            header_line = stream.readline()

            if not header_line:
                log.info("LSP stdout stream ended while reading headers.")
                return None

            if header_line == b"\r\n":
                # Blank line signifies end of headers
                break

            # Check for Content-Length header
            match = CONTENT_LENGTH_RE.match(header_line)
            if match:
                content_length = int(match.group(1))
            # else: Ignore other headers like Content-Type

        if content_length == -1:
            log.warning("Did not find Content-Length header before blank line.")
            return None

        # Check if body data is available before reading
        if not select.select([stream], [], [], timeout)[0]:
            log.info("Timeout waiting for message body after headers")
            return None

        # Read the JSON payload body
        body = stream.read(content_length)
        if len(body) < content_length:
            log.error(
                f"LSP stdout stream ended prematurely while reading body. Expected {content_length}, got {len(body)}."
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
        # Catch potential errors during readline() or read()
        if lsp_process:  # Check if process termination was intended
            log.error(f"Unexpected error reading LSP stdout: {e}", exc_info=True)
        else:
            log.info(f"Error reading LSP stdout after process termination: {e}")

    return None


# --- Stderr Reader Thread ---
def _read_stderr(stream):
    """Reads stderr from the LSP process for logging."""
    try:
        while True:
            # Use select to check if there's data to read (timeout of 0.5 seconds)
            if not select.select([stream], [], [], 0.5)[0]:
                # No data available, continue and check again
                continue

            # Data is available, read as many lines as possible
            stderr_lines = []
            while select.select([stream], [], [], 0)[0]:  # Non-blocking check
                line = stream.readline()
                if not line:
                    log.debug("LSP stderr stream ended.")
                    return  # Exit the function if stream has ended

                stderr_lines.append(line.decode("utf-8", errors="ignore").strip())

            # If we have collected any lines, log them as a single block
            if stderr_lines:
                stderr_block = "\n".join(stderr_lines)
                log.info(f"LSP stderr output:\n{stderr_block}")

    except Exception as e:
        # Check if process still exists before logging error
        if lsp_process:
            log.error(f"Error reading LSP stderr: {e}", exc_info=True)
        else:
            log.info(f"Error reading LSP stderr after process termination: {e}")
    finally:
        log.info("LSP stderr reader thread finished.")


# --- Core LSP Management Functions ---


def start_lsp_process(python_executable: str):
    """Starts the jedi-language-server subprocess for a given session."""
    global lsp_process, lsp_stderr_reader, lsp_write_lock

    if lsp_process:
        log.warning("LSP process already running. Stopping it first.")
        stop_lsp_process()

    jedi_path = Path(python_executable).parent / "jedi-language-server"
    log.info(f"Starting LSP process using: {jedi_path}")
    try:
        cmd = [jedi_path]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,  # Important for unbuffered I/O
        )
        lsp_process = proc

        # Create a dedicated lock for this process's stdin
        lsp_write_lock = threading.Lock()

        # Start only the stderr reader thread
        stderr_thread = threading.Thread(
            target=_read_stderr, args=(proc.stderr,), daemon=True
        )
        lsp_stderr_reader = stderr_thread
        stderr_thread.start()

        log.info(
            f"LSP process started (PID: {proc.pid}). Stderr reader thread running."
        )
        return True  # Indicate success

    except FileNotFoundError:
        log.error(f"Jedi-language-server executable not found: {jedi_path}")
        return False
    except Exception as e:
        log.error(f"Failed to start LSP process: {e}", exc_info=True)
        # Clean up if proc was partially created
        if lsp_process:
            _stop_lsp_process_internal()
        return False


def _cleanup_lsp_resources():
    """Internal helper to remove a session's resources from dictionaries."""
    global lsp_process, lsp_stderr_reader, lsp_write_lock
    lsp_process = None
    lsp_stderr_reader = None
    lsp_write_lock = None


def _stop_lsp_process_internal():
    """Stops the LSP process without acquiring the lock (for internal use)."""
    proc = lsp_process
    if proc:
        log.info(f"Stopping LSP process (PID: {proc.pid}).")
        try:
            # Close stdin first to signal EOF to LSP server
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except OSError as e:
            log.warning(f"Error closing LSP stdin: {e}")

        try:
            # Terminate the process gracefully first
            proc.terminate()
            # Wait for a short time for graceful exit
            try:
                proc.wait(timeout=2)
                log.info("LSP process terminated gracefully.")
            except subprocess.TimeoutExpired:
                log.warning("LSP process did not terminate gracefully, killing.")
                proc.kill()
                proc.wait(timeout=1)  # Wait briefly after kill
                log.info("LSP process killed.")

        except Exception as e:
            log.error(f"Error stopping LSP process: {e}", exc_info=True)
        finally:
            # Ensure resources are removed even if stopping fails
            _cleanup_lsp_resources()
    else:
        log.info("No active LSP process found to stop.")
        # Still ensure cleanup in case of dangling dictionary entries
        _cleanup_lsp_resources()

    # Wait for stderr reader thread to finish (it should exit when pipes close)
    if lsp_stderr_reader and lsp_stderr_reader.is_alive():
        log.debug("Waiting for stderr reader thread to join...")
        lsp_stderr_reader.join(timeout=1)

    log.info("LSP process and thread stopped.")


def stop_lsp_process():
    """Stops the jedi-language-server subprocess and cleans up resources for a given session."""
    _stop_lsp_process_internal()


def send_lsp_message(sid: str, message: dict, socketio_emit: Callable):
    """Sends a message to the LSP process for the given session and reads the response."""
    log.info(
        f"Preparing to send LSP message: {message.get('method')}, {message.get('id')}"
    )
    # pretty print the message
    log.info(f"LSP message: {json.dumps(message, indent=2)}")

    if lsp_process and lsp_process.stdin and not lsp_process.stdin.closed:
        formatted_message = _format_lsp_message(message)
        if not formatted_message:
            log.error(f"Failed to format message, not sending: {message}")
            return
        try:
            with lsp_write_lock:
                lsp_process.stdin.write(formatted_message)
                lsp_process.stdin.flush()

                # Check message type to determine if a response is expected
                # LSP notifications don't require responses - they use method but no id
                expects_response = "id" in message

                if expects_response:
                    # Read the response synchronously with timeout
                    response = _read_one_lsp_message(lsp_process.stdout, timeout=5.0)
                    if response:
                        # Emit the response using the provided emit function
                        socketio_emit("lsp_response", response, room=sid)
                    else:
                        log.warning(
                            f"No response received for message with id: {message.get('id')}"
                        )
                else:
                    log.debug("Message is a notification, not waiting for response")

        except BrokenPipeError:
            log.error(
                "LSP process stdin pipe broke while writing. Process likely died."
            )
            # Trigger cleanup as the process is gone
            stop_lsp_process()
        except Exception as e:
            log.error(
                f"Error writing to LSP stdin or reading response: {e}", exc_info=True
            )
    elif not lsp_process:
        log.warning("No active LSP process found to send message to.")
    else:
        log.warning("LSP process stdin is closed, cannot send message.")
