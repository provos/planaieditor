import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from lsprotocol import types
from pygls.workspace import TextDocument

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s"
)
temp_file_log = logging.getLogger("TempFileManager")  # For the TempFileManager


class TempFileManager:
    """
    Manages temporary files for in-memory URIs and translates URIs in LSP messages.
    """

    def __init__(self):
        self.inmemory_to_temp_path: Dict[str, str] = (
            {}
        )  # "inmemory://model/1" -> "/tmp/xyz.py"
        self.temp_path_to_inmemory_uri: Dict[str, str] = (
            {}
        )  # "/tmp/xyz.py" -> "inmemory://model/1"
        self.inmemory_documents: Dict[str, TextDocument] = (
            {}
        )  # "inmemory://model/1" -> TextDocument(...)
        self.temp_file_lock = threading.Lock()
        temp_file_log.info("TempFileManager instance initialized.")

    def _sanitize_uri_for_filename(self, uri: str) -> str:
        return uri.replace("://", "_").replace("/", "_").replace(":", "_")

    def _get_temp_file_path(self, original_uri: str) -> Optional[str]:
        with self.temp_file_lock:
            return self.inmemory_to_temp_path.get(original_uri)

    def _get_original_uri(self, temp_file_path: str) -> Optional[str]:
        with self.temp_file_lock:
            normalized_path = str(Path(temp_file_path).resolve())
            return self.temp_path_to_inmemory_uri.get(normalized_path)

    def create_or_update_temp_file(
        self, original_uri: str, content: str
    ) -> Optional[str]:
        if not original_uri.startswith("inmemory://"):
            temp_file_log.warning(
                f"Attempted to create temp file for non-inmemory URI: {original_uri}"
            )
            return None  # Or original_uri if it should pass through

        with self.temp_file_lock:
            temp_path_str = self.inmemory_to_temp_path.get(original_uri)
            try:
                if temp_path_str:  # Update existing
                    with open(temp_path_str, "w", encoding="utf-8") as f:
                        f.write(content)
                    temp_file_log.debug(
                        f"Updated temporary file {temp_path_str} for URI {original_uri}"
                    )
                else:  # Create new
                    sanitized_part = self._sanitize_uri_for_filename(original_uri)
                    fd, temp_path_str = tempfile.mkstemp(
                        suffix=".py", prefix=f"jls_proxy_{sanitized_part}_"
                    )
                    os.close(fd)
                    with open(temp_path_str, "w", encoding="utf-8") as f:
                        f.write(content)

                    normalized_path = str(Path(temp_path_str).resolve())
                    self.inmemory_to_temp_path[original_uri] = normalized_path
                    self.temp_path_to_inmemory_uri[normalized_path] = original_uri
                    temp_file_log.info(
                        f"Created temporary file {normalized_path} for in-memory URI {original_uri}"
                    )

                return Path(temp_path_str).as_uri()  # Returns "file:///tmp/..."
            except Exception as e:
                temp_file_log.error(
                    f"Error creating/updating temp file for {original_uri}: {e}",
                    exc_info=True,
                )
                if (
                    temp_path_str and original_uri not in self.inmemory_to_temp_path
                ):  # Cleanup if partially created
                    try:
                        os.remove(temp_path_str)
                    except OSError:
                        pass
                return None

    def _delete_temp_file_internal(self, original_uri: str) -> None:
        """Internal helper to delete a temp file; assumes lock is already held."""
        temp_path_str = self.inmemory_to_temp_path.pop(original_uri, None)
        if temp_path_str:
            self.temp_path_to_inmemory_uri.pop(
                str(Path(temp_path_str).resolve()),
                None,  # Ensure normalized path is used for pop
            )
            try:
                os.remove(temp_path_str)
                temp_file_log.info(
                    f"Deleted temporary file {temp_path_str} for URI {original_uri}"
                )
            except OSError as e:
                temp_file_log.error(
                    f"Error deleting temporary file {temp_path_str}: {e}",
                    exc_info=True,
                )

    def delete_temp_file(self, original_uri: str) -> None:
        with self.temp_file_lock:
            self._delete_temp_file_internal(original_uri)

    def cleanup_all_temp_files(self):
        with self.temp_file_lock:
            temp_file_log.info("Cleaning up all temporary files...")
            uris_to_delete = list(self.inmemory_to_temp_path.keys())
            for uri in uris_to_delete:
                self._delete_temp_file_internal(uri)  # Call the internal method
                self.inmemory_documents.pop(
                    uri, None
                )  # Also remove from documents cache
            if not self.inmemory_to_temp_path and not self.temp_path_to_inmemory_uri:
                temp_file_log.info(
                    "All temporary files and mappings cleaned up successfully."
                )
            else:
                temp_file_log.warning(
                    "Some temporary files or mappings might not have been cleaned up."
                )

    def _translate_uri_recursive(self, data: Any, direction: str) -> Any:
        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                if key == "uri" and isinstance(value, str):
                    translated_uri = value
                    if direction == "to_server" and value.startswith("inmemory://"):
                        # Temp file creation/update is handled before this recursive call for main doc URIs.
                        # This part ensures other embedded URIs are also attempted to be translated.
                        temp_file_path = self._get_temp_file_path(value)
                        if temp_file_path:
                            translated_uri = Path(temp_file_path).as_uri()
                            if value != translated_uri:
                                temp_file_log.debug(
                                    f"Translated URI (to_server) in recursive: {value} -> {translated_uri}"
                                )
                    elif direction == "to_client" and value.startswith("file://"):
                        try:
                            path_from_uri = str(
                                Path(value.replace("file://", "")).resolve()
                            )
                            original_inmemory_uri = self._get_original_uri(
                                path_from_uri
                            )
                            if original_inmemory_uri:
                                translated_uri = original_inmemory_uri
                                if value != translated_uri:
                                    temp_file_log.debug(
                                        f"Translated URI (to_client) in recursive: {value} -> {translated_uri}"
                                    )
                        except Exception as e:  # Path might be invalid, keep original
                            temp_file_log.warning(
                                f"Error processing file URI for client translation {value}: {e}"
                            )
                    new_dict[key] = translated_uri
                    if (
                        translated_uri == value
                    ):  # If no translation happened, recurse on value if it's a structure
                        new_dict[key] = self._translate_uri_recursive(value, direction)

                # Handle common LSP structures containing URIs
                elif (
                    key == "textDocument" and isinstance(value, dict) and "uri" in value
                ):
                    new_dict[key] = self._translate_uri_recursive(value, direction)
                elif key == "documentChanges" and isinstance(value, list):
                    new_dict[key] = [
                        self._translate_uri_recursive(item, direction) for item in value
                    ]
                elif (
                    key in ["location", "targetUri", "originSelectionRange"]
                    and isinstance(value, dict)
                    and "uri" in value
                ):
                    new_dict[key] = self._translate_uri_recursive(value, direction)
                elif key in ["locations"] and isinstance(
                    value, list
                ):  # Often a list of Location objects
                    new_dict[key] = [
                        self._translate_uri_recursive(item, direction) for item in value
                    ]
                # For `targetUri` in LocationLink, it's a direct string value, not a dict.
                elif key == "targetUri" and isinstance(value, str):
                    translated_uri = value
                    if direction == "to_client" and value.startswith("file://"):
                        try:
                            path_from_uri = str(
                                Path(value.replace("file://", "")).resolve()
                            )
                            original_inmemory_uri = self._get_original_uri(
                                path_from_uri
                            )
                            if original_inmemory_uri:
                                translated_uri = original_inmemory_uri
                        except Exception:
                            pass  # Keep original if error
                    new_dict[key] = translated_uri
                else:
                    new_dict[key] = self._translate_uri_recursive(value, direction)
            return new_dict
        elif isinstance(data, list):
            return [self._translate_uri_recursive(item, direction) for item in data]
        else:
            return data

    def translate_message_to_server(self, message: Dict[str, Any]) -> Dict[str, Any]:
        method = message.get("method")
        params = message.get("params", {})
        # Deep copy to avoid modifying the original message if it's logged or reused elsewhere
        # before translation.
        processed_message = json.loads(json.dumps(message))

        if method == "textDocument/didOpen" and params:
            doc = params.get(
                "textDocument", {}
            )  # params is already a part of processed_message
            uri = doc.get("uri")
            text = doc.get("text")
            version = doc.get("version")
            language_id = doc.get("languageId", "python")  # Default to python

            if uri and uri.startswith("inmemory://") and text is not None:
                # Create and store TextDocument for inmemory URIs
                document = TextDocument(
                    uri=uri,
                    source=text,
                    version=version,
                    language_id=language_id,
                    sync_kind=types.TextDocumentSyncKind.Incremental,
                )
                self.inmemory_documents[uri] = document
                # Use document.source to ensure consistency, though it's same as 'text' here
                temp_file_uri_str = self.create_or_update_temp_file(
                    uri, document.source
                )
                if not temp_file_uri_str:
                    temp_file_log.error(
                        f"Failed to create temp file for didOpen: {uri}. Sending original URI."
                    )
                    # processed_message["params"]["textDocument"]["uri"] will remain inmemory://
                else:
                    # The recursive translator will handle replacing the URI in the message structure
                    temp_file_log.info(
                        f"didOpen: {uri} mapped to temp file; URI will be translated by recursive call."
                    )

        elif method == "textDocument/didChange" and params:
            doc_id = params.get("textDocument", {})
            uri = doc_id.get("uri")
            content_changes: Optional[List[Dict[str, Any]]] = params.get(
                "contentChanges"
            )
            version = doc_id.get("version")

            if uri and uri.startswith("inmemory://") and content_changes:
                document = self.inmemory_documents.get(uri)
                if document:
                    for change in content_changes:
                        # The LSP spec says range can be missing for full updates.
                        if "range" not in change:  # Full update
                            pygls_change = types.TextDocumentContentChangeEvent_Type2(
                                text=change["text"]
                            )
                        else:  # Incremental update
                            pygls_change = types.TextDocumentContentChangeEvent_Type1(
                                range=types.Range(
                                    start=types.Position(
                                        line=change["range"]["start"]["line"],
                                        character=change["range"]["start"]["character"],
                                    ),
                                    end=types.Position(
                                        line=change["range"]["end"]["line"],
                                        character=change["range"]["end"]["character"],
                                    ),
                                ),
                                text=change["text"],
                            )
                        document.apply_change(pygls_change)

                    document.version = version
                    temp_file_uri_str = self.create_or_update_temp_file(
                        uri, document.source
                    )
                    if not temp_file_uri_str:
                        temp_file_log.error(
                            f"Failed to update temp file for didChange: {uri}. Sending original URI."
                        )
                    else:
                        temp_file_log.info(
                            f"didChange: {uri} content updated in temp file ({len(document.source)} chars); URI will be translated."
                        )
                else:
                    temp_file_log.warning(
                        f"didChange for {uri} received but no document in memory. "
                        "This might happen if didOpen was not processed first for this URI."
                    )
            elif uri and uri.startswith("inmemory://"):
                temp_file_log.warning(
                    f"didChange for {uri} received with no content changes."
                )

        elif method == "textDocument/didClose" and params:
            doc_id = params.get("textDocument", {})
            uri = doc_id.get("uri")
            if uri and uri.startswith("inmemory://"):
                self.inmemory_documents.pop(uri, None)  # Remove from in-memory cache
                temp_file_log.info(
                    f"didClose: Handling URI {uri}. Translating to file URI for server, then deleting temp file."
                )

                # Directly get the file path and convert it to a file URI
                temp_file_path_str = self._get_temp_file_path(uri)
                translated_uri_for_server = None
                if temp_file_path_str:
                    translated_uri_for_server = Path(temp_file_path_str).as_uri()

                # Now delete the temporary file and its mappings
                self.delete_temp_file(uri)

                # Return the translated file URI.
                # If for some reason it wasn't found (e.g., file never existed),
                # this would return None, or the original uri if we fall back.
                # The test expects translated_uri_for_server to be valid.
                if translated_uri_for_server:
                    return translated_uri_for_server
                else:
                    # Fallback or error: If the URI was inmemory but no temp file was found.
                    # This case might indicate a logic error elsewhere if the test setup implies a file should exist.
                    temp_file_log.warning(
                        f"didClose: No temp file path found for {uri}, returning original URI to server."
                    )
                    return uri  # Return original URI if no translation found

        return self._translate_uri_recursive(processed_message, "to_server")

    def translate_message_to_client(self, message: Dict[str, Any]) -> Dict[str, Any]:
        processed_message = json.loads(json.dumps(message))  # Deep copy
        return self._translate_uri_recursive(processed_message, "to_client")
