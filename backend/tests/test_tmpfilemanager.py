import logging
import os
import unittest
from pathlib import Path

# Assuming the project root 'planaieditor' is in PYTHONPATH
# or tests are run in an environment where this import works.
from planaieditor.tmpfilemanager import TempFileManager

# Suppress logging from TempFileManager during tests to keep test output clean
logging.getLogger("TempFileManager").setLevel(logging.CRITICAL + 1)


class TestTempFileManager(unittest.TestCase):
    def setUp(self):
        self.manager = TempFileManager()

    def tearDown(self):
        self.manager.cleanup_all_temp_files()

    def test_create_new_temp_file(self):
        uri = "inmemory://model/1"
        content = "print('hello world')"
        file_uri_str = self.manager.create_or_update_temp_file(uri, content)

        self.assertIsNotNone(file_uri_str)
        self.assertTrue(file_uri_str.startswith("file:///"))

        temp_path_str = self.manager._get_temp_file_path(uri)
        self.assertIsNotNone(temp_path_str)
        self.assertTrue(
            os.path.exists(temp_path_str), f"Temp file {temp_path_str} should exist."
        )

        with open(temp_path_str, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

        normalized_temp_path = str(Path(temp_path_str).resolve())
        self.assertEqual(self.manager._get_original_uri(normalized_temp_path), uri)

    def test_update_existing_temp_file(self):
        uri = "inmemory://model/update_test"
        initial_content = "initial content"
        updated_content = "updated content"

        self.manager.create_or_update_temp_file(uri, initial_content)
        temp_path_str = self.manager._get_temp_file_path(uri)
        self.assertIsNotNone(temp_path_str)

        file_uri_str = self.manager.create_or_update_temp_file(uri, updated_content)
        self.assertIsNotNone(file_uri_str)
        self.assertTrue(
            file_uri_str.startswith("file:///")
        )  # Should return the same file URI

        self.assertTrue(os.path.exists(temp_path_str))
        with open(temp_path_str, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), updated_content)

    def test_create_temp_file_for_non_inmemory_uri(self):
        uri = "file:///some/local/file.py"
        content = "this content should not be written to a new temp file"
        # Current behavior: returns None for non-inmemory URIs
        returned_path = self.manager.create_or_update_temp_file(uri, content)
        self.assertIsNone(returned_path)
        self.assertIsNone(self.manager._get_temp_file_path(uri))

    def test_delete_temp_file(self):
        uri = "inmemory://model/to_delete"
        content = "delete me"
        self.manager.create_or_update_temp_file(uri, content)
        temp_path_str = self.manager._get_temp_file_path(uri)
        self.assertIsNotNone(temp_path_str)
        self.assertTrue(os.path.exists(temp_path_str))

        self.manager.delete_temp_file(uri)

        self.assertFalse(os.path.exists(temp_path_str))
        self.assertIsNone(self.manager._get_temp_file_path(uri))
        self.assertIsNone(self.manager._get_original_uri(temp_path_str))

    def test_delete_non_existent_temp_file(self):
        uri = "inmemory://model/non_existent"
        # Should not raise an error
        self.manager.delete_temp_file(uri)
        self.assertIsNone(self.manager._get_temp_file_path(uri))

    def test_cleanup_all_temp_files(self):
        uri1 = "inmemory://model/cleanup1"
        uri2 = "inmemory://model/cleanup2"
        self.manager.create_or_update_temp_file(uri1, "content1")
        self.manager.create_or_update_temp_file(uri2, "content2")

        path1 = self.manager._get_temp_file_path(uri1)
        path2 = self.manager._get_temp_file_path(uri2)
        self.assertTrue(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))
        self.assertGreater(len(self.manager.inmemory_to_temp_path), 0)

        self.manager.cleanup_all_temp_files()

        self.assertFalse(os.path.exists(path1), f"File {path1} should be deleted.")
        self.assertFalse(os.path.exists(path2), f"File {path2} should be deleted.")
        self.assertEqual(len(self.manager.inmemory_to_temp_path), 0)
        self.assertEqual(len(self.manager.temp_path_to_inmemory_uri), 0)

    def test_translate_did_open_to_server(self):
        original_uri = "inmemory://model/test_doc_open.py"
        content = "def hello():\n  pass"
        message = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": original_uri,
                    "languageId": "python",
                    "version": 1,
                    "text": content,
                }
            },
        }
        translated_message = self.manager.translate_message_to_server(message)
        temp_physical_path = self.manager._get_temp_file_path(original_uri)

        self.assertIsNotNone(temp_physical_path)
        self.assertTrue(os.path.exists(temp_physical_path))
        with open(temp_physical_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

        translated_uri_in_msg = translated_message["params"]["textDocument"]["uri"]
        self.assertTrue(translated_uri_in_msg.startswith("file:///"))
        self.assertEqual(
            Path(translated_uri_in_msg.replace("file://", "")).resolve(),
            Path(temp_physical_path).resolve(),
        )

    def test_translate_did_change_to_server(self):
        original_uri = "inmemory://model/change_doc.py"
        initial_content = "initial content"
        # Simulate didOpen first to correctly initialize TextDocument in the manager
        open_message = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": original_uri,
                    "languageId": "python",
                    "version": 1,
                    "text": initial_content,
                }
            },
        }
        self.manager.translate_message_to_server(open_message)
        temp_physical_path = self.manager._get_temp_file_path(original_uri)
        self.assertIsNotNone(
            temp_physical_path, "Temp file should be created by didOpen"
        )
        self.assertTrue(
            os.path.exists(temp_physical_path), "Temp file should exist after didOpen"
        )
        with open(temp_physical_path, "r", encoding="utf-8") as f:
            self.assertEqual(
                f.read(), initial_content, "Content should be initial after didOpen"
            )

        new_content = "updated content"
        change_message = {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": original_uri, "version": 2},
                "contentChanges": [{"text": new_content}],
            },
        }
        translated_message = self.manager.translate_message_to_server(change_message)

        self.assertTrue(os.path.exists(temp_physical_path))
        with open(temp_physical_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), new_content)

        translated_uri_in_msg = translated_message["params"]["textDocument"]["uri"]
        self.assertTrue(translated_uri_in_msg.startswith("file:///"))
        self.assertEqual(
            Path(translated_uri_in_msg.replace("file://", "")).resolve(),
            Path(temp_physical_path).resolve(),
        )
        self.assertEqual(
            translated_message["params"]["contentChanges"][0]["text"], new_content
        )

    def test_translate_did_close_to_server(self):
        original_uri = "inmemory://model/close_me.py"
        content = "content_to_be_deleted"
        expected_file_uri_str = self.manager.create_or_update_temp_file(
            original_uri, content
        )
        self.assertIsNotNone(expected_file_uri_str)

        temp_physical_path_before_close = self.manager._get_temp_file_path(original_uri)
        self.assertTrue(os.path.exists(temp_physical_path_before_close))

        message = {
            "jsonrpc": "2.0",
            "method": "textDocument/didClose",
            "params": {"textDocument": {"uri": original_uri}},
        }
        # With the fix, translate_message_to_server for didClose directly returns the translated URI string.
        returned_message = self.manager.translate_message_to_server(message)

        # The returned URI should be the file URI, and the temp file should be deleted.
        self.assertEqual(
            returned_message["params"]["textDocument"]["uri"],
            expected_file_uri_str,
            f"The returned URI '{returned_message['params']['textDocument']['uri']}' should be the translated file URI '{expected_file_uri_str}'.",
        )

        self.assertFalse(
            os.path.exists(temp_physical_path_before_close),
            "Temp file should be deleted.",
        )
        self.assertIsNone(self.manager._get_temp_file_path(original_uri))
        self.assertIsNone(
            self.manager._get_original_uri(
                str(Path(expected_file_uri_str.replace("file://", "")).resolve())
            )
        )

    def test_translate_publish_diagnostics_to_client(self):
        original_uri = "inmemory://model/diagnostics_test.py"
        content = "import sys"
        temp_file_uri_str = self.manager.create_or_update_temp_file(
            original_uri, content
        )
        self.assertIsNotNone(temp_file_uri_str)

        message_from_server = {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": temp_file_uri_str,  # This is the file:/// URI
                "diagnostics": [{"range": {}, "message": "Syntax error"}],
            },
        }
        translated_message = self.manager.translate_message_to_client(
            message_from_server
        )
        self.assertEqual(translated_message["params"]["uri"], original_uri)

    def test_translate_nested_uri_to_server(self):
        original_nested_uri = "inmemory://model/nested_doc.py"
        content = "some python code"
        # Ensure the URI is known so it *can* be translated
        self.manager.create_or_update_temp_file(original_nested_uri, content)
        temp_physical_path = self.manager._get_temp_file_path(original_nested_uri)

        message = {
            "method": "someLspMethod",
            "params": {
                "outerKey": {
                    "uri": original_nested_uri  # This 'uri' key should be translated
                }
            },
        }
        translated_message = self.manager.translate_message_to_server(message)
        translated_nested_uri = translated_message["params"]["outerKey"]["uri"]
        self.assertTrue(translated_nested_uri.startswith("file:///"))
        self.assertEqual(
            Path(translated_nested_uri.replace("file://", "")).resolve(),
            Path(temp_physical_path).resolve(),
        )

    def test_translate_nested_uri_to_client(self):
        original_nested_uri = "inmemory://model/client_nested.py"
        content = "client nested content"
        temp_file_uri_str = self.manager.create_or_update_temp_file(
            original_nested_uri, content
        )  # file:///...
        self.assertIsNotNone(temp_file_uri_str)

        message_from_server = {
            "method": "lspResponse",
            "result": {"references": [{"uri": temp_file_uri_str, "range": {}}]},
        }
        translated_message = self.manager.translate_message_to_client(
            message_from_server
        )
        translated_nested_uri = translated_message["result"]["references"][0]["uri"]
        self.assertEqual(translated_nested_uri, original_nested_uri)

    def test_translate_target_uri_to_server(self):
        original_target_uri = "inmemory://model/target_to_server.py"
        content = "target content"
        self.manager.create_or_update_temp_file(original_target_uri, content)
        # temp_physical_path = self.manager._get_temp_file_path(original_target_uri) # For assertion if translated

        message = {
            "method": "goToDefinition",
            "params": {
                "textDocument": {"uri": "inmemory://model/source.py"},
                "position": {},
                "targetUri": original_target_uri,
            },
        }
        # Ensure source.py also has a mapping if it were to be translated (not the focus here)
        self.manager.create_or_update_temp_file("inmemory://model/source.py", "")

        translated_message = self.manager.translate_message_to_server(message)
        translated_target_uri = translated_message["params"]["targetUri"]

        # Current behavior: 'targetUri' (if string) is NOT translated from inmemory:// to file:// for 'to_server'
        # It only has specific 'to_client' logic.
        # The general 'uri' key translation is specific to key == 'uri'.
        self.assertEqual(
            translated_target_uri,
            original_target_uri,
            "targetUri (string) should not be translated to file:// for server in current impl.",
        )

    def test_translate_target_uri_to_client(self):
        original_target_uri = "inmemory://model/target_to_client.py"
        content = "client target content"
        temp_file_uri_str = self.manager.create_or_update_temp_file(
            original_target_uri, content
        )  # file:///...
        self.assertIsNotNone(temp_file_uri_str)

        message_from_server = {
            "method": "definitionResponse",
            "result": {"targetUri": temp_file_uri_str, "targetRange": {}},
        }
        translated_message = self.manager.translate_message_to_client(
            message_from_server
        )
        translated_target_uri = translated_message["result"]["targetUri"]
        self.assertEqual(translated_target_uri, original_target_uri)

    def test_uri_translation_for_unknown_file_uri_to_client(self):
        unknown_file_uri = "file:///var/tmp/some_other_file.py"
        message_from_server = {
            "method": "textDocument/publishDiagnostics",
            "params": {"uri": unknown_file_uri, "diagnostics": []},
        }
        translated_message = self.manager.translate_message_to_client(
            message_from_server
        )
        # URI should remain unchanged as it's not managed by TempFileManager
        self.assertEqual(translated_message["params"]["uri"], unknown_file_uri)

    def test_uri_translation_for_unhandled_inmemory_uri_to_server(self):
        # This inmemory URI is not passed to create_or_update_temp_file first
        unhandled_inmemory_uri = "inmemory://model/unhandled.py"
        message = {
            "method": "textDocument/definition",
            "params": {"textDocument": {"uri": unhandled_inmemory_uri}},
        }
        translated_message = self.manager.translate_message_to_server(message)
        # URI should remain unchanged as no temp file was created for it
        self.assertEqual(
            translated_message["params"]["textDocument"]["uri"], unhandled_inmemory_uri
        )

    def test_translate_incremental_did_change_to_server(self):
        original_uri = "inmemory://model/incremental_change_doc.py"
        initial_content = "line one\nline two\nline three"

        # 1. Simulate didOpen
        open_message = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": original_uri,
                    "languageId": "python",
                    "version": 1,
                    "text": initial_content,
                }
            },
        }
        self.manager.translate_message_to_server(open_message)
        temp_physical_path = self.manager._get_temp_file_path(original_uri)
        self.assertIsNotNone(temp_physical_path)
        with open(temp_physical_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), initial_content)

        # 2. Define and apply an incremental change (e.g., replace 'two' with 'TWO_MODIFIED')
        change_event = {
            "range": {
                "start": {"line": 1, "character": 5},  # Start of 'two'
                "end": {"line": 1, "character": 8},  # End of 'two'
            },
            "text": "TWO_MODIFIED",
        }

        change_message = {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": original_uri, "version": 2},
                "contentChanges": [change_event],
            },
        }
        self.manager.translate_message_to_server(change_message)

        # 3. Verify the content of the temp file
        expected_content_after_change = "line one\nline TWO_MODIFIED\nline three"
        self.assertTrue(os.path.exists(temp_physical_path))
        with open(temp_physical_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), expected_content_after_change)


if __name__ == "__main__":
    unittest.main()
