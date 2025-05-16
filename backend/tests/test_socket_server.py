import threading
import time
import unittest
from typing import Any, Dict
from unittest.mock import patch

# Import the module from its new location
from planaieditor.socket_server import SocketClient, SocketServer, send_debug_event


class TestSocketServer(unittest.TestCase):
    """Test cases for the SocketServer class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a list to store received messages
        self.received_messages = []

        # Define a callback function for the server
        def message_callback(message: Dict[str, Any]):
            self.received_messages.append(message)

        self.callback = message_callback

    def tearDown(self):
        """Clean up after tests."""
        self.received_messages.clear()

    def test_server_init(self):
        """Test that the server initializes correctly."""
        server = SocketServer(callback=self.callback)
        self.assertEqual(server.host, "127.0.0.1")
        self.assertEqual(server.port, 0)  # Default is auto-assign
        self.assertTrue(callable(server.callback))

        # Test with custom params
        server = SocketServer(
            callback=self.callback,
            host="localhost",
            port=5050,
            buffer_size=8192,
            encoding="ascii",
            delimiter="|",
            timeout=0.5,
        )
        self.assertEqual(server.host, "localhost")
        self.assertEqual(server.port, 5050)
        self.assertEqual(server.buffer_size, 8192)
        self.assertEqual(server.encoding, "ascii")
        self.assertEqual(server.delimiter, "|")
        self.assertEqual(server.timeout, 0.5)

    def test_server_context_manager(self):
        """Test that the server works as a context manager."""
        with SocketServer(callback=self.callback) as server:
            self.assertIsNotNone(server._server_socket)
            self.assertTrue(server._running)
            self.assertIsNotNone(server.port)
            self.assertGreater(server.port, 0)  # Port should be assigned

        # After context exit, server should be stopped
        self.assertFalse(server._running)
        self.assertIsNone(server._server_socket)

    def test_socket_client_init(self):
        """Test that the client initializes correctly."""
        client = SocketClient()
        self.assertEqual(client.host, "127.0.0.1")
        self.assertEqual(client.port, 0)

        # Test with custom params
        client = SocketClient(
            host="localhost",
            port=5050,
            encoding="ascii",
            delimiter="|",
            connect_timeout=2.0,
        )
        self.assertEqual(client.host, "localhost")
        self.assertEqual(client.port, 5050)
        self.assertEqual(client.encoding, "ascii")
        self.assertEqual(client.delimiter, "|")
        self.assertEqual(client.connect_timeout, 2.0)

    def test_client_connect_error(self):
        """Test client error handling when connection fails."""
        client = SocketClient(port=54321)  # Use a port likely not in use

        # Should raise ValueError if trying to connect without a port
        no_port_client = SocketClient(port=0)
        with self.assertRaises(ValueError):
            no_port_client.connect()

        # Should return False when send fails
        self.assertFalse(client.send({"test": "message"}))

    def test_client_context_manager(self):
        """Test that client works as a context manager when server is running."""
        with SocketServer(callback=self.callback) as server:
            # Mock the connect and disconnect methods
            with patch.object(SocketClient, "connect") as mock_connect, patch.object(
                SocketClient, "disconnect"
            ) as mock_disconnect:

                with SocketClient(port=server.port):
                    mock_connect.assert_called_once()

                mock_disconnect.assert_called_once()

    def test_server_client_integration(self):
        """Test that the server and client can communicate properly."""
        # Start the server with our callback
        with SocketServer(callback=self.callback) as server:
            # Connect a client
            client = SocketClient(port=server.port)
            client.connect()

            # Send a test message
            test_message = {"type": "test", "data": {"value": 123}}
            success = client.send(test_message)
            self.assertTrue(success)

            # Give the server time to process the message
            time.sleep(0.1)

            # Check that the message was received
            self.assertEqual(len(self.received_messages), 1)
            self.assertEqual(self.received_messages[0], test_message)

            # Clean up
            client.disconnect()

    def test_send_debug_event_function(self):
        """Test the send_debug_event convenience function."""
        with SocketServer(callback=self.callback) as server:
            port = server.port

            # Test with explicit port
            success = send_debug_event("test_event", {"key": "value"}, port=port)
            self.assertTrue(success)

            # Test with environment variable
            with patch.dict("os.environ", {"DEBUG_PORT": str(port)}):
                success = send_debug_event("env_event", {"env": True})
                self.assertTrue(success)

            # Give server time to process
            time.sleep(0.1)

            # Check both messages were received
            self.assertEqual(len(self.received_messages), 2)
            self.assertEqual(self.received_messages[0]["type"], "test_event")
            self.assertEqual(self.received_messages[1]["type"], "env_event")

    def test_multiple_clients(self):
        """Test that the server can handle multiple clients."""
        with SocketServer(callback=self.callback) as server:
            # Create and connect multiple clients
            clients = []
            for i in range(3):
                client = SocketClient(port=server.port)
                client.connect()
                clients.append(client)

            # Each client sends a message
            for i, client in enumerate(clients):
                client.send({"client_id": i, "message": f"Hello from client {i}"})

            # Give server time to process
            time.sleep(0.2)

            # Verify all messages were received
            self.assertEqual(len(self.received_messages), 3)

            # Clean up
            for client in clients:
                client.disconnect()

    def test_server_stops_gracefully(self):
        """Test that the server stops gracefully even with active clients."""
        server = SocketServer(callback=self.callback)
        server.start()

        # Connect a client
        client = SocketClient(port=server.port)
        client.connect()

        # Stop the server
        server.stop()

        # Server should be fully stopped
        self.assertFalse(server._running)
        self.assertIsNone(server._server_socket)

        attempts = 0
        while attempts < 10:
            # There seems to be a timing problem when running on GitHub Actions.
            # This is a hack to make sure the server is fully stopped.
            time.sleep(1)
            attempts += 1
            # Client should not be able to send after server stops
            result = client.send({"test": "message"})
            if not result:
                break

        self.assertFalse(result, "Client should not be able to send after server stops")


class TestServerStress(unittest.TestCase):
    """Additional stress tests for the socket server."""

    def setUp(self):
        """Set up test fixtures."""
        self.received_messages = []
        self.message_count_lock = threading.Lock()

        def message_callback(message: Dict[str, Any]):
            with self.message_count_lock:
                self.received_messages.append(message)

        self.callback = message_callback

    def tearDown(self):
        """Clean up after tests."""
        self.received_messages.clear()

    def test_rapid_messages(self):
        """Test sending many messages in rapid succession."""
        NUM_MESSAGES = 50

        with SocketServer(callback=self.callback) as server:
            client = SocketClient(port=server.port)
            client.connect()

            # Send many messages in quick succession
            for i in range(NUM_MESSAGES):
                client.send({"index": i, "data": f"Message {i}"})

            # Give time for processing
            time.sleep(0.5)

            # Verify all messages were received (in any order)
            with self.message_count_lock:
                self.assertEqual(len(self.received_messages), NUM_MESSAGES)

                # Check that all indices are present
                indices = {msg["index"] for msg in self.received_messages}
                self.assertEqual(len(indices), NUM_MESSAGES)

            client.disconnect()

    def test_concurrent_clients(self):
        """Test concurrent client connections and message sending."""
        NUM_CLIENTS = 5
        MSGS_PER_CLIENT = 10

        def client_worker(client_id):
            with SocketClient(port=server.port) as client:
                for i in range(MSGS_PER_CLIENT):
                    client.send(
                        {
                            "client_id": client_id,
                            "msg_id": i,
                            "data": f"Client {client_id}, Message {i}",
                        }
                    )
                    # Small random delay to simulate real-world usage
                    time.sleep(0.01)

        with SocketServer(callback=self.callback) as server:
            # Start client threads
            threads = []
            for i in range(NUM_CLIENTS):
                thread = threading.Thread(target=client_worker, args=(i,))
                thread.start()
                threads.append(thread)

            # Wait for all clients to finish
            for thread in threads:
                thread.join()

            # Give server time to process any remaining messages
            time.sleep(0.2)

            # Verify all messages were received
            self.assertEqual(len(self.received_messages), NUM_CLIENTS * MSGS_PER_CLIENT)

            # Check distribution of messages from clients
            client_counts = {}
            for msg in self.received_messages:
                client_id = msg["client_id"]
                client_counts[client_id] = client_counts.get(client_id, 0) + 1

            # Each client should have sent exactly MSGS_PER_CLIENT messages
            for i in range(NUM_CLIENTS):
                self.assertEqual(client_counts.get(i, 0), MSGS_PER_CLIENT)


if __name__ == "__main__":
    unittest.main()
