import json
import os
import sys
import time
import unittest
from pathlib import Path
from queue import Empty, Queue

from planaieditor.lsp_handler import LSPHandler


class TestLSPHandlerIntegration(unittest.TestCase):
    lsp_handler: LSPHandler
    mock_emit_queue: Queue
    python_executable: str
    session_id: str

    @classmethod
    def setUpClass(cls):
        cls.python_executable = sys.executable
        # Check if jedi-language-server is likely available
        jedi_path = Path(cls.python_executable).parent / "jedi-language-server"
        jedi_path_exe = Path(cls.python_executable).parent / "jedi-language-server.exe"
        if not jedi_path.exists() and not jedi_path_exe.exists():
            raise unittest.SkipTest(
                f"jedi-language-server not found near {cls.python_executable}, skipping integration test."
            )
        cls.session_id = "test_lsp_session_main_replication"

    def setUp(self):
        # Create a new LSPHandler instance for each test to ensure isolation
        self.lsp_handler = LSPHandler(write_log=False)  # Disable file logging for tests
        self.mock_emit_queue = Queue()
        self.current_id = 0

    def tearDown(self):
        self.lsp_handler.stop_lsp_process()

    def mock_socketio_emit(self, event: str, data: dict, room: str):
        # print(f"MOCK EMIT Captured: Event={event}, Room={room}, SID={self.session_id}, Data={json.dumps(data, indent=2)}")
        if room == self.session_id:
            self.mock_emit_queue.put({"event": event, "data": data, "room": room})
            print(
                f"MOCK EMIT Captured: Event={event}, Room={room}, SID={self.session_id}, Data={json.dumps(data, indent=2)}"
            )
        else:
            print(
                f"MOCK EMIT Warning: Message for unexpected room {room}, expected {self.session_id}"
            )

    def get_next_emitted_message(self, timeout: float = 10.0) -> dict:
        try:
            # Drain any previous messages not consumed, useful if server is chatty
            while True:
                msg = self.mock_emit_queue.get(block=False)
                print(
                    f"Drained old message: {msg['data'].get('method') or msg['data'].get('id')}"
                )
        except Empty:
            pass  # Queue is now empty, proceed to wait for the desired message

        try:
            return self.mock_emit_queue.get(timeout=timeout)
        except Empty:
            self.fail(f"Timeout waiting for message from LSP server after {timeout}s")
        return {}  # Should not be reached

    def send_and_assert_initialize(self):
        init_msg_id = self.current_id
        self.current_id += 1
        init_msg = {
            "jsonrpc": "2.0",
            "id": init_msg_id,
            "method": "initialize",
            "params": {
                "processId": os.getpid(),  # Can be None or actual pid
                "clientInfo": {"name": "TestClient", "version": "1.0"},
                "rootUri": Path(
                    os.getcwd()
                ).as_uri(),  # Test running from project root usually
                "capabilities": {
                    # Basic capabilities, jedi-language-server is tolerant
                    "textDocument": {
                        "codeAction": {
                            "codeActionLiteralSupport": {
                                "codeActionKind": {
                                    "valueSet": [
                                        "",
                                        "quickfix",
                                        "refactor",
                                        "refactor.extract",
                                        "refactor.inline",
                                        "refactor.rewrite",
                                        "source",
                                        "source.organizeImports",
                                    ]
                                }
                            }
                        }
                    }
                },
                "trace": "verbose",  # As in example
                "workspaceFolders": [
                    {"uri": Path(os.getcwd()).as_uri(), "name": "workspace"}
                ],
            },
        }
        self.lsp_handler.send_lsp_message(init_msg)

        response = self.get_next_emitted_message(timeout=15.0)  # Init can be slow
        self.assertEqual(response["data"]["id"], init_msg_id)
        self.assertIn("capabilities", response["data"]["result"])
        self.assertEqual(
            response["data"]["result"]["serverInfo"]["name"], "jedi-language-server"
        )

    def send_and_assert_open(self, file_uri: str, file_content: str):
        # Text from the log (via lsp_handler.py main example):
        # L0: import os
        # L1: (empty)
        # L2: def main_func():
        # L3:     print(os.getpid())
        # L4:     # A comment for action

        did_open_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": file_uri,
                    "languageId": "python",
                    "version": 1,  # Version 1 as per log
                    "text": file_content,
                }
            },
        }
        self.lsp_handler.send_lsp_message(did_open_msg)

        # Expect textDocument/publishDiagnostics
        diag_response = self.get_next_emitted_message(timeout=5.0)
        self.assertEqual(
            diag_response["data"]["method"], "textDocument/publishDiagnostics"
        )
        self.assertEqual(diag_response["data"]["params"]["uri"], file_uri)
        # Diagnostics can be empty or not, depending on linter/server. Log shows empty.
        self.assertEqual(diag_response["data"]["params"]["diagnostics"], [])

    def send_and_assert_hover(self, file_uri: str):
        hover_id = self.current_id
        self.current_id += 1
        hover_msg = {
            "jsonrpc": "2.0",
            "id": hover_id,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": file_uri},
                "position": {"line": 3, "character": 7},
            },
        }

        self.lsp_handler.send_lsp_message(hover_msg)
        hover_response = self.get_next_emitted_message(timeout=5.0)
        self.assertEqual(hover_response["data"]["id"], hover_id)
        self.assertIn("result", hover_response["data"])

        expected_hover_result = {
            "contents": {
                "kind": "plaintext",
                "value": "def print(*values: object, sep: Optional[str]=..., end: Optional[str]=..., file: Optional[SupportsWrite[str]]=..., flush: bool=...) -> None\n---\nprint(value, ..., sep=' ', end='\\n', file=sys.stdout, flush=False)\n\nPrints the values to a stream, or to sys.stdout by default.\nOptional keyword arguments:\nfile:  a file-like object (stream); defaults to the current sys.stdout.\nsep:   string inserted between values, default a space.\nend:   string appended after the last value, default a newline.\nflush: whether to forcibly flush the stream.\nFull name: builtins.print",
            },
            "range": {
                "start": {"line": 3, "character": 4},
                "end": {"line": 3, "character": 9},
            },
        }
        self.assertEqual(hover_response["data"]["result"], expected_hover_result)

    def send_and_assert_code_action(self, file_uri: str):
        code_action_id = self.current_id
        self.current_id += 1

        # Range from the log's request: (line 3, character 7)
        # This corresponds to L3: `    print(os.g|etpid())` in 0-indexed lines
        code_action_request_range = {
            "start": {"line": 3, "character": 7},
            "end": {"line": 3, "character": 7},
        }
        code_action_msg = {
            "jsonrpc": "2.0",
            "id": code_action_id,
            "method": "textDocument/codeAction",
            "params": {
                "textDocument": {"uri": file_uri},
                "range": code_action_request_range,
                "context": {"diagnostics": []},  # As in log
            },
        }
        self.lsp_handler.send_lsp_message(code_action_msg)

        action_response = self.get_next_emitted_message(
            timeout=10.0
        )  # Jedi can take time
        self.assertEqual(action_response["data"]["id"], code_action_id)

        actions_result = action_response["data"]["result"]
        self.assertIsInstance(
            actions_result, list, "CodeAction result should be a list."
        )

        # Verify the specific "Extract expression into variable..." action from the log
        found_extract_variable_action = False
        expected_edits_for_extract_var = [
            {
                "range": {
                    "start": {"line": 3, "character": 4},
                    "end": {"line": 3, "character": 4},
                },
                "newText": "jls_extract_var = ",
            },
            {
                "range": {
                    "start": {"line": 3, "character": 9},
                    "end": {"line": 3, "character": 9},
                },
                "newText": "\n    jls_extract_var",
            },
        ]

        for action in actions_result:
            if (
                action.get("title")
                == "Extract expression into variable 'jls_extract_var'"
            ):
                found_extract_variable_action = True
                self.assertEqual(action.get("kind"), "refactor.extract")
                self.assertIn("edit", action)
                workspace_edit = action["edit"]
                self.assertIn("documentChanges", workspace_edit)
                doc_changes = workspace_edit["documentChanges"]
                self.assertEqual(len(doc_changes), 1)
                text_doc_edit = doc_changes[0]
                self.assertEqual(text_doc_edit["textDocument"]["uri"], file_uri)
                self.assertEqual(
                    text_doc_edit["textDocument"]["version"], 1
                )  # Matching opened version

                # Sort both lists of edits for comparison, as order might not be guaranteed
                # Edits are dictionaries, so we need a consistent way to sort them (e.g., by newText then range)
                def key_func(edit):
                    return (
                        edit["newText"],
                        json.dumps(edit["range"]["start"]),
                        json.dumps(edit["range"]["end"]),
                    )

                sorted_actual_edits = sorted(text_doc_edit["edits"], key=key_func)
                sorted_expected_edits = sorted(
                    expected_edits_for_extract_var, key=key_func
                )

                self.assertEqual(
                    sorted_actual_edits,
                    sorted_expected_edits,
                    f"Edits for 'Extract variable' do not match log. Got: {json.dumps(sorted_actual_edits, indent=2)}",
                )
                break

        self.assertTrue(
            found_extract_variable_action,
            "Did not find the 'Extract expression into variable...' action from the log.",
        )

    def send_close(self, file_uri: str):
        did_close_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didClose",
            "params": {"textDocument": {"uri": file_uri}},
        }
        self.lsp_handler.send_lsp_message(did_close_msg)
        time.sleep(0.5)  # Allow server to process, as in main()

    def test_end_to_end_workflow(self):
        self.assertTrue(
            self.lsp_handler.start_lsp_process(
                self.python_executable, self.session_id, self.mock_socketio_emit
            ),
            "LSP process should start successfully.",
        )

        # 1. Initialize
        self.send_and_assert_initialize()
        # 2. Initialized
        initialized_msg = {"jsonrpc": "2.0", "method": "initialized", "params": {}}
        self.lsp_handler.send_lsp_message(initialized_msg)
        # No direct response, but wait a bit for server to process
        time.sleep(0.5)

        # 3. textDocument/didOpen (matching the log's content and URI)
        file_content = "import os\n\ndef main_func():\n    print(os.getpid())\n    # A comment for action\n"
        file_uri = "inmemory://project/file1.py"  # URI from the log
        self.send_and_assert_open(file_uri, file_content)

        # 4. textDocument/codeAction (matching the log's request and expected response)
        self.send_and_assert_code_action(file_uri)
        # 5. textDocument/hover
        self.send_and_assert_hover(file_uri)

        # 6. textDocument/didClose
        self.send_close(file_uri)

        # 7. Shutdown
        # In the lsp_handler.py main() example and its provided successful execution log,
        # the mock_emit_main function does NOT show a printout for the shutdown response (ID 100).
        # This suggests that either it's not consistently received/processed before exit in that
        # specific execution flow, or main() simply doesn't wait for it.
        # To replicate main() based on its logs, we send shutdown, sleep, then send exit,
        # without asserting a response for shutdown.
        shutdown_id = 100  # ID from the log, though we won't assert its response
        shutdown_msg = {"jsonrpc": "2.0", "id": shutdown_id, "method": "shutdown"}
        self.lsp_handler.send_lsp_message(shutdown_msg)
        time.sleep(
            1
        )  # Mimic main's sleep after sending shutdown and before sending exit

        # 8. Exit
        exit_msg = {"jsonrpc": "2.0", "method": "exit"}
        self.lsp_handler.send_lsp_message(exit_msg)
        time.sleep(1)  # Mimic main's sleep after sending exit.
        # The tearDown method will call stop_lsp_process() to ensure cleanup.


if __name__ == "__main__":
    unittest.main()
