import json
import logging
import re  # Import regex for header parsing
import subprocess
import threading
from pathlib import Path
from typing import Callable, Dict

# Configure basic logging for the LSP handler
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - [LSPHandler] %(message)s"
)
log = logging.getLogger(__name__)

# --- Global Dictionaries to Manage LSP Subprocesses ---
# Structure: {sid: subprocess.Popen}
lsp_processes: Dict[str, subprocess.Popen] = {}
# Structure: {sid: threading.Thread} - For reading LSP stdout
lsp_stdout_readers: Dict[str, threading.Thread] = {}
# Structure: {sid: threading.Thread} - For reading LSP stderr
lsp_stderr_readers: Dict[str, threading.Thread] = {}
# Structure: {sid: queue.Queue} - For sending messages *to* the LSP process thread-safely (Alternative to direct proc.stdin.write)
# lsp_write_queues: Dict[str, queue.Queue] = {}

# Regex to find Content-Length header
CONTENT_LENGTH_RE = re.compile(rb"^Content-Length: *(\d+)\r\n", re.IGNORECASE)

# Lock for modifying the shared dictionaries
_lsp_dict_lock = threading.Lock()

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


# --- Reader Thread Implementation ---
def _read_lsp_messages(stream, sid: str, socketio_emit: Callable):
    """Reads LSP messages from the stream (stdout) and emits them via SocketIO."""
    try:
        while True:
            content_length = -1
            # Read header lines until a blank line is encountered
            while True:
                header_line = stream.readline()
                if not header_line:
                    log.info(f"[{sid}] LSP stdout stream ended while reading headers.")
                    # Use break instead of return to allow finally block execution
                    raise EOFError("Stream ended while reading headers")  # Or break

                if header_line == b"\r\n":
                    # Blank line signifies end of headers
                    break

                # Check for Content-Length header
                match = CONTENT_LENGTH_RE.match(header_line)
                if match:
                    content_length = int(match.group(1))
                # else: Ignore other headers like Content-Type

            if content_length == -1:
                log.warning(
                    f"[{sid}] Did not find Content-Length header before blank line."
                )
                continue  # Try reading next message block

            # Read the JSON payload body
            body = stream.read(content_length)
            if len(body) < content_length:
                log.error(
                    f"[{sid}] LSP stdout stream ended prematurely while reading body. Expected {content_length}, got {len(body)}."
                )
                break  # Incomplete read

            try:
                payload = json.loads(body.decode("utf-8"))
                log.debug(
                    f"[{sid}] Received LSP Message: {payload.get('method', payload.get('id', ''))}"
                )
                # Emit the parsed JSON payload to the correct client
                socketio_emit("lsp_response", payload, room=sid)
            except json.JSONDecodeError as e:
                log.error(
                    f"[{sid}] Failed to decode LSP JSON payload: {e}. Payload: {body.decode('utf-8', errors='ignore')}",
                    exc_info=True,
                )
            except Exception as e:
                log.error(
                    f"[{sid}] Error processing received LSP message: {e}", exc_info=True
                )

    # Handle specific stream end cases gracefully
    except EOFError as e:
        log.info(f"[{sid}] LSP stream ended expectedly: {e}")
    except BrokenPipeError:
        log.info(f"[{sid}] LSP process stdout pipe broke (likely process termination).")
    except Exception as e:
        # Catch potential errors during readline() or read()
        with _lsp_dict_lock:  # Ensure thread-safe access to lsp_processes
            process_exists = sid in lsp_processes
        if process_exists:  # Check if process termination was intended
            log.error(
                f"[{sid}] Unexpected error reading LSP stdout: {e}", exc_info=True
            )
        else:
            log.info(f"[{sid}] Error reading LSP stdout after process termination: {e}")
    finally:
        log.info(f"[{sid}] LSP stdout reader thread finished.")
        # Optionally signal that the connection is dead if needed
        # socketio_emit('lsp_disconnected', {'sid': sid}, broadcast=True) # Example


# --- Stderr Reader Thread ---
def _read_stderr(stream, sid: str):
    """Reads stderr from the LSP process for logging."""
    try:
        while True:
            line = stream.readline()
            if not line:
                log.info(f"[{sid}] LSP stderr stream ended.")
                break
            log.info(
                f"[{sid}] LSP stderr: {line.decode('utf-8', errors='ignore').strip()}"
            )
    except Exception as e:
        # Check if process still exists before logging error
        with _lsp_dict_lock:
            process_exists = sid in lsp_processes
        if process_exists:
            log.error(f"[{sid}] Error reading LSP stderr: {e}", exc_info=True)
        else:
            log.info(f"[{sid}] Error reading LSP stderr after process termination: {e}")
    finally:
        log.info(f"[{sid}] LSP stderr reader thread finished.")


# --- Core LSP Management Functions ---


def start_lsp_process(sid: str, python_executable: str, socketio_emit: Callable):
    """Starts the jedi-language-server subprocess for a given session."""
    with _lsp_dict_lock:
        if sid in lsp_processes:
            log.warning(f"[{sid}] LSP process already running. Stopping existing one.")
            # Call internal stop without acquiring lock again
            _stop_lsp_process_internal(sid)

        jedi_path = Path(python_executable).parent / "jedi-language-server"
        log.info(f"[{sid}] Starting LSP process using: {jedi_path}")
        try:
            cmd = [jedi_path]
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,  # Important for unbuffered I/O
            )
            lsp_processes[sid] = proc

            # Start reader threads
            stdout_thread = threading.Thread(
                target=_read_lsp_messages,
                args=(proc.stdout, sid, socketio_emit),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_read_stderr, args=(proc.stderr, sid), daemon=True
            )
            lsp_stdout_readers[sid] = stdout_thread
            lsp_stderr_readers[sid] = stderr_thread

            stdout_thread.start()
            stderr_thread.start()

            log.info(
                f"[{sid}] LSP process started (PID: {proc.pid}). Reader threads running."
            )
            return True  # Indicate success

        except FileNotFoundError:
            log.error(f"[{sid}] Jedi-language-server executable not found: {jedi_path}")
            return False
        except Exception as e:
            log.error(f"[{sid}] Failed to start LSP process: {e}", exc_info=True)
            # Clean up if proc was partially created
            if sid in lsp_processes:
                _stop_lsp_process_internal(sid)
            return False


def _cleanup_lsp_resources(sid: str):
    """Internal helper to remove a session's resources from dictionaries."""
    lsp_processes.pop(sid, None)
    lsp_stdout_readers.pop(sid, None)
    lsp_stderr_readers.pop(sid, None)
    # lsp_write_queues.pop(sid, None)


def _stop_lsp_process_internal(sid: str):
    """Stops the LSP process without acquiring the lock (for internal use)."""
    proc = lsp_processes.get(sid)
    if proc:
        log.info(f"[{sid}] Stopping LSP process (PID: {proc.pid}).")
        try:
            # Close stdin first to signal EOF to LSP server
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except OSError as e:
            log.warning(f"[{sid}] Error closing LSP stdin: {e}")

        try:
            # Terminate the process gracefully first
            proc.terminate()
            # Wait for a short time for graceful exit
            try:
                proc.wait(timeout=2)
                log.info(f"[{sid}] LSP process terminated gracefully.")
            except subprocess.TimeoutExpired:
                log.warning(
                    f"[{sid}] LSP process did not terminate gracefully, killing."
                )
                proc.kill()
                proc.wait(timeout=1)  # Wait briefly after kill
                log.info(f"[{sid}] LSP process killed.")

        except Exception as e:
            log.error(f"[{sid}] Error stopping LSP process: {e}", exc_info=True)
        finally:
            # Ensure resources are removed even if stopping fails
            _cleanup_lsp_resources(sid)
    else:
        log.info(f"[{sid}] No active LSP process found to stop.")
        # Still ensure cleanup in case of dangling dictionary entries
        _cleanup_lsp_resources(sid)

    # Wait for reader threads to finish (they should exit when pipes close)
    stdout_thread = lsp_stdout_readers.get(sid)
    stderr_thread = lsp_stderr_readers.get(sid)
    if stdout_thread and stdout_thread.is_alive():
        log.debug(f"[{sid}] Waiting for stdout reader thread to join...")
        stdout_thread.join(timeout=1)
    if stderr_thread and stderr_thread.is_alive():
        log.debug(f"[{sid}] Waiting for stderr reader thread to join...")
        stderr_thread.join(timeout=1)

    log.info(f"[{sid}] LSP process and threads stopped.")


def stop_lsp_process(sid: str):
    """Stops the jedi-language-server subprocess and cleans up resources for a given session."""
    with _lsp_dict_lock:
        _stop_lsp_process_internal(sid)


def send_lsp_message(sid: str, message: dict):
    """Sends a message to the LSP process for the given session."""
    log.debug(
        f"[{sid}] Preparing to send LSP message: {message.get('method', message.get('id', ''))}"
    )
    proc = None
    with _lsp_dict_lock:
        proc = lsp_processes.get(sid)

    if proc and proc.stdin and not proc.stdin.closed:
        formatted_message = _format_lsp_message(message)
        if not formatted_message:
            log.error(f"[{sid}] Failed to format message, not sending: {message}")
            return
        try:
            proc.stdin.write(formatted_message)
            proc.stdin.flush()
            log.debug(f"[{sid}] Message sent to LSP process.")
        except BrokenPipeError:
            log.error(
                f"[{sid}] LSP process stdin pipe broke while writing. Process likely died."
            )
            # Trigger cleanup as the process is gone
            stop_lsp_process(sid)
        except Exception as e:
            log.error(f"[{sid}] Error writing to LSP stdin: {e}", exc_info=True)
    elif not proc:
        log.warning(f"[{sid}] No active LSP process found to send message to.")
    else:
        log.warning(f"[{sid}] LSP process stdin is closed, cannot send message.")
