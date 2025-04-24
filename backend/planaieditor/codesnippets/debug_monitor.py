import json
import os
from typing import Any, Dict, Optional

# Simplified SocketClient implementation for injection into subprocess
import socket


def send_debug_event(
    event_type: str,
    data: Dict[str, Any],
    port: Optional[str] = None,
    host: str = "127.0.0.1",
) -> bool:
    """Send a debug event to the socket server."""
    if not port:
        port = os.environ.get("DEBUG_PORT")
        if not port:
            raise ValueError(
                "WARNING: DEBUG_PORT environment variable not set, cannot send debug events"
            )

    message = {"type": event_type, "data": data}
    message_str = json.dumps(message) + "\n"

    try:
        # Create a socket and connect to the server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)  # 1 second timeout
            s.connect((host, int(port)))
            s.sendall(message_str.encode("utf-8"))
        return True
    except Exception as e:
        print(f"ERROR: Failed to send debug event: {e}")
        return False
