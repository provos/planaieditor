import os
from pathlib import Path

from flask import Flask, jsonify, request, send_file

ALLOWED_EXTENSIONS = [".py", ".json", ".jsonl", ".txt"]


def sanitize_path(root_path: Path, requested_path: str) -> Path:
    input_path = "./" + str(requested_path)
    full_path = (root_path / Path(input_path)).resolve()
    if not str(full_path).startswith(str(root_path)):
        raise ValueError(f"Attempt to access path outside root: {full_path}")

    return full_path


def setup_filesystem(app: Flask, root_path: Path):
    if not root_path.is_dir():
        raise ValueError(f"Root path '{root_path}' is not a valid directory.")

    # Ensure root_path is absolute and resolved for security checks
    absolute_root_path = root_path.resolve()
    app.logger.info(f"Filesystem root configured at: {absolute_root_path}")

    @app.route("/api/filesystem/list", methods=["GET"])
    def list_filesystem():
        requested_path_str = request.args.get("path", default="/", type=str)
        app.logger.debug(f"Received list request for path: {requested_path_str}")

        try:
            # Create a secure path relative to the root
            full_path = sanitize_path(absolute_root_path, requested_path_str)

            if not full_path.exists():
                app.logger.warning(f"Path not found: {full_path}")
                return jsonify({"message": f"Path not found: {full_path}"}), 404

            if not full_path.is_dir():
                app.logger.warning(f"Path is not a directory: {full_path}")
                return (
                    jsonify({"message": f"Path is not a directory: {full_path}"}),
                    400,
                )

            items = []
            for item in full_path.iterdir():
                try:
                    is_dir = item.is_dir()
                    if not is_dir:
                        extension = item.suffix
                        if extension not in ALLOWED_EXTENSIONS:
                            continue

                    relative_item_path = item.relative_to(absolute_root_path)
                    # Ensure each path starts with a forward slash for consistent API
                    item_path_str = "/" + str(relative_item_path).replace(os.sep, "/")
                    items.append(
                        {
                            "name": item.name,
                            "type": "directory" if is_dir else "file",
                            "path": item_path_str,
                        }
                    )
                except OSError as e:
                    # Log error for files/dirs we might not have access to, but continue listing others
                    app.logger.error(f"Error accessing item {item}: {e}")
                except ValueError as e:
                    # Should not happen if iterdir is within root, but log just in case
                    app.logger.error(f"Error calculating relative path for {item}: {e}")

            display_path = "/" + str(full_path.relative_to(absolute_root_path)).replace(
                os.sep, "/"
            )
            if display_path == "/.":
                display_path = "/"

            app.logger.debug(f"Successfully listed items for: {display_path}")
            return jsonify({"path": display_path, "items": items}), 200

        except ValueError as e:
            # Specifically handle path validation errors (like traversal attempts)
            app.logger.warning(f"Path validation error for '{requested_path_str}': {e}")
            return jsonify({"message": f"Access denied: {e}"}), 403
        except Exception as e:
            app.logger.error(
                f"Unexpected error in list_filesystem for path '{requested_path_str}': {e}",
                exc_info=True,
            )
            return jsonify({"message": "An internal server error occurred."}), 500

    @app.route("/api/filesystem/read", methods=["GET"])
    def read_filesystem():
        requested_path_str = request.args.get("path", type=str)
        if not requested_path_str:
            return jsonify({"message": "Missing 'path' query parameter."}), 400
        app.logger.debug(f"Received read request for path: {requested_path_str}")

        try:
            full_path = sanitize_path(absolute_root_path, requested_path_str)

            if not full_path.exists():
                app.logger.warning(f"Read request: Path not found: {full_path}")
                return jsonify({"message": "File not found."}), 404

            if not full_path.is_file():
                app.logger.warning(f"Read request: Path is not a file: {full_path}")
                return jsonify({"message": "Path is not a file."}), 400

            extension = full_path.suffix
            if extension not in ALLOWED_EXTENSIONS:
                app.logger.warning(
                    f"Read request: Path has disallowed extension: {full_path}"
                )
                return jsonify({"message": "Path has disallowed extension."}), 400

            # Use send_file for efficient file sending and potential MIME type detection
            app.logger.info(f"Sending file: {full_path}")
            # consider adding as_attachment=True if download is desired
            return send_file(full_path)

        except ValueError as e:  # Catch specific path validation errors
            app.logger.error(
                f"Path validation error for read request '{requested_path_str}': {e}"
            )
            return jsonify({"message": f"Access denied: {e}"}), 403  # Forbidden
        except (
            FileNotFoundError
        ):  # Should be caught by full_path.exists() but good practice
            app.logger.warning(
                f"Read request: File not found (secondary check): {full_path}"
            )
            return jsonify({"message": "File not found."}), 404
        except PermissionError:
            app.logger.error(f"Permission denied trying to read file: {full_path}")
            return jsonify({"message": "Permission denied."}), 403
        except Exception as e:
            app.logger.error(
                f"Unexpected error in read_filesystem for path '{requested_path_str}': {e}",
                exc_info=True,
            )
            return (
                jsonify(
                    {"message": "An internal server error occurred reading the file."}
                ),
                500,
            )

    @app.route("/api/filesystem/write", methods=["POST"])
    def write_filesystem():
        if not request.is_json:
            return jsonify({"message": "Request must be JSON."}), 400

        data = request.get_json()
        requested_path_str = data.get("path")
        content = data.get("content")

        if (
            not requested_path_str or content is None
        ):  # Check content for None explicitly
            return (
                jsonify({"message": "Missing 'path' or 'content' in JSON body."}),
                400,
            )

        app.logger.debug(f"Received write request for path: {requested_path_str}")

        try:
            # Sanitize the *full* path first to ensure the target location is valid
            full_path = sanitize_path(absolute_root_path, requested_path_str)

            extension = full_path.suffix
            if extension not in ALLOWED_EXTENSIONS:
                app.logger.warning(
                    f"Write request: Path has disallowed extension: {full_path}"
                )
                return jsonify({"message": "Path has disallowed extension."}), 400

            # Now, check the parent directory to ensure it exists and is writable within the root
            parent_dir = full_path.parent
            if not parent_dir.exists():
                app.logger.warning(
                    f"Write request: Parent directory does not exist: {parent_dir}"
                )
                return jsonify({"message": "Parent directory does not exist."}), 400
            if not parent_dir.is_dir():
                app.logger.warning(
                    f"Write request: Parent path is not a directory: {parent_dir}"
                )
                return jsonify({"message": "Invalid target directory."}), 400
            # Re-verify parent is within root (should be covered by full_path check, but belts and suspenders)
            if (
                absolute_root_path != parent_dir
                and absolute_root_path not in parent_dir.parents
            ):
                app.logger.error(
                    f"Write request: Parent directory {parent_dir} ended up outside root {absolute_root_path} (SECURITY ISSUE)"
                )
                return jsonify({"message": "Access denied."}), 403

            # Filename Sanitization (Basic): Ensure the final component (filename) is safe.
            # For simplicity, we rely on the initial sanitize_path resolving,
            # but more complex rules could be added here (e.g., allowed chars).
            # The Path object itself handles OS-specific invalid chars to some extent.

            # Write the content
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                app.logger.info(f"Successfully wrote file: {full_path}")
                # Return path relative to root
                relative_path_str = "/" + str(
                    full_path.relative_to(absolute_root_path)
                ).replace(os.sep, "/")
                if relative_path_str == "/.":
                    relative_path_str = "/"
                return (
                    jsonify(
                        {
                            "message": "File saved successfully.",
                            "path": relative_path_str,
                        }
                    ),
                    200,
                )  # 200 OK as overwrite is allowed

            except OSError as e:
                app.logger.error(f"Error writing file {full_path}: {e}")
                # Check for permission error specifically if possible (OS-dependent)
                if isinstance(e, PermissionError):
                    return jsonify({"message": "Permission denied."}), 403
                else:
                    return jsonify({"message": f"Could not write file: {e}"}), 500

        except ValueError as e:  # Catch path validation errors
            app.logger.error(
                f"Path validation error for write request '{requested_path_str}': {e}"
            )
            return jsonify({"message": f"Access denied: {e}"}), 403  # Forbidden
        except Exception as e:
            app.logger.error(
                f"Unexpected error in write_filesystem for path '{requested_path_str}': {e}",
                exc_info=True,
            )
            return (
                jsonify(
                    {"message": "An internal server error occurred saving the file."}
                ),
                500,
            )
