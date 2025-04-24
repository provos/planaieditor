import json
import logging
import socket
import threading
import time
from typing import Any, Callable, Dict, Optional, Union

logger = logging.getLogger(__name__)


class SocketServer:
    """
    A lightweight socket server for inter-process communication using a context manager pattern.

    Example usage:
    ```python
    def handle_message(message):
        print(f"Received: {message}")

    with SocketServer(callback=handle_message) as server:
        subprocess_env = os.environ.copy()
        subprocess_env['DEBUG_PORT'] = str(server.port)
        subprocess.Popen([python_path, script_path], env=subprocess_env)

        # Socket server runs in background until context exits
    ```
    """

    def __init__(
        self,
        callback: Callable[[Dict[str, Any]], None],
        host: str = "127.0.0.1",
        port: int = 0,  # 0 means use any available port
        buffer_size: int = 4096,
        encoding: str = "utf-8",
        delimiter: str = "\n",
        timeout: float = 0.1,
    ):
        """
        Initialize the socket server.

        Args:
            callback: Function to call with each received message (parsed from JSON)
            host: Host to bind the server to
            port: Port to bind to (0 = auto-assign an available port)
            buffer_size: Size of the receive buffer
            encoding: Character encoding for messages
            delimiter: Message delimiter (default: newline)
            timeout: Socket timeout in seconds
        """
        self.callback = callback
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.encoding = encoding
        self.delimiter = delimiter
        self.timeout = timeout

        self._server_socket = None
        self._running = False
        self._thread = None
        self._clients = []
        self._lock = threading.Lock()

    def __enter__(self):
        """Start the server when entering the context."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the server when exiting the context."""
        self.stop()
        return False  # Let exceptions propagate

    def start(self):
        """Start the socket server in a background thread."""
        if self._running:
            return

        # Create and configure the server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        self._server_socket.settimeout(self.timeout)

        # Get the actual port (if auto-assigned)
        _, self.port = self._server_socket.getsockname()

        logger.info(f"Socket server started on {self.host}:{self.port}")

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the socket server."""
        if not self._running:
            return

        logger.info("Stopping socket server...")
        self._running = False

        # Close all client connections
        with self._lock:
            for client_socket in self._clients:
                try:
                    client_socket.close()
                except Exception as e:
                    logger.error(f"Error closing client socket: {e}")
            self._clients.clear()

        # Close the server socket
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")
            self._server_socket = None

        # Wait for the thread to terminate
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                logger.warning("Socket server thread did not terminate gracefully")

        logger.info("Socket server stopped")

    def _run(self):
        """Main server loop that accepts connections and processes messages."""
        while self._running:
            try:
                # Accept new connections
                try:
                    client_socket, addr = self._server_socket.accept()
                    client_socket.settimeout(self.timeout)
                    logger.debug(f"New connection from {addr}")

                    with self._lock:
                        self._clients.append(client_socket)

                    # Start a thread to handle this client
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, addr),
                        daemon=True,
                    )
                    client_thread.start()

                except socket.timeout:
                    # No new connections, just continue
                    continue
                except Exception as e:
                    if self._running:  # Only log if we're still meant to be running
                        logger.error(f"Error accepting connection: {e}")
                    break

            except Exception as e:
                logger.error(f"Error in server loop: {e}")
                if not self._running:
                    break
                time.sleep(0.1)  # Prevent tight loop in case of persistent errors

    def _handle_client(self, client_socket, addr):
        """Handle communication with a single client."""
        buffer = b""

        try:
            while self._running:
                try:
                    # Receive data
                    chunk = client_socket.recv(self.buffer_size)
                    if not chunk:
                        break  # Client disconnected

                    buffer += chunk

                    # Process complete messages
                    while self.delimiter.encode(self.encoding) in buffer:
                        # Split at the delimiter
                        message_bytes, buffer = buffer.split(
                            self.delimiter.encode(self.encoding), 1
                        )

                        # Decode and parse the message
                        message_str = message_bytes.decode(self.encoding)
                        try:
                            message = json.loads(message_str)
                            # Call the callback with the parsed message
                            self.callback(message)
                        except json.JSONDecodeError as e:
                            logger.error(
                                f"Invalid JSON received: {e}, message: {message_str[:100]}..."
                            )

                except socket.timeout:
                    # Socket timeout, just continue
                    continue
                except Exception as e:
                    if self._running:  # Only log if we're still meant to be running
                        logger.error(f"Error handling client {addr}: {e}")
                    break

        finally:
            # Clean up
            try:
                client_socket.close()
            except Exception:
                pass

            with self._lock:
                if client_socket in self._clients:
                    self._clients.remove(client_socket)

            logger.debug(f"Connection from {addr} closed")


class SocketClient:
    """
    A lightweight socket client for sending messages to the server.

    Example usage:
    ```python
    # In subprocess
    client = SocketClient(port=os.environ.get('DEBUG_PORT'))
    client.send({"event": "task_scheduled", "data": {...}})
    ```
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: Union[int, str] = 0,
        encoding: str = "utf-8",
        delimiter: str = "\n",
        connect_timeout: float = 5.0,
    ):
        """
        Initialize the socket client.

        Args:
            host: Host to connect to
            port: Port to connect to (can be string or int)
            encoding: Character encoding for messages
            delimiter: Message delimiter
            connect_timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = int(port) if port else 0
        self.encoding = encoding
        self.delimiter = delimiter
        self.connect_timeout = connect_timeout
        self._socket = None

    def connect(self):
        """Connect to the server."""
        if self._socket:
            return

        if not self.port:
            raise ValueError("Port must be specified")

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self.connect_timeout)
        self._socket.connect((self.host, self.port))

    def disconnect(self):
        """Disconnect from the server."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def send(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to the server.

        Args:
            message: Dictionary to send (will be converted to JSON)

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._socket:
            try:
                self.connect()
            except Exception as e:
                logger.error(f"Failed to connect: {e}")
                return False

        try:
            # Convert the message to JSON and append the delimiter
            message_str = json.dumps(message) + self.delimiter
            message_bytes = message_str.encode(self.encoding)

            # Send the message
            self._socket.sendall(message_bytes)
            return True

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            # Attempt to reconnect on next send
            self.disconnect()
            return False

    def __enter__(self):
        """Connect when entering context."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Disconnect when exiting context."""
        self.disconnect()
        return False  # Let exceptions propagate


def send_debug_event(
    event_type: str,
    data: Dict[str, Any],
    port: Optional[Union[int, str]] = None,
    host: str = "127.0.0.1",
) -> bool:
    """
    Convenience function to send a debug event to the socket server.

    Args:
        event_type: Type of the event (e.g., "task_scheduled")
        data: Event data
        port: Server port (can be string or int, typically from environment variable)
        host: Server host

    Returns:
        bool: True if successful, False otherwise
    """
    if not port:
        # Check environment variable
        import os

        port = os.environ.get("DEBUG_PORT")
        if not port:
            logger.warning("DEBUG_PORT not set, cannot send debug event")
            return False

    message = {"type": event_type, "data": data}

    # Use context manager for automatic connection/disconnection
    with SocketClient(host=host, port=port) as client:
        return client.send(message)
