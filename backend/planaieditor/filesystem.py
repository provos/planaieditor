import os
from pathlib import Path

from flask import Flask, jsonify, request



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
        requested_path_str = request.args.get("path", default=".", type=str)
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
                    # Construct path relative to the *original* request root for the frontend
                    relative_item_path = item.relative_to(absolute_root_path)
                    items.append(
                        {
                            "name": item.name,
                            "type": "directory" if is_dir else "file",
                            "path": str(relative_item_path).replace(
                                os.sep, "/"
                            ),  # Use forward slashes for consistency
                        }
                    )
                except OSError as e:
                    # Log error for files/dirs we might not have access to, but continue listing others
                    app.logger.error(f"Error accessing item {item}: {e}")
                except ValueError as e:
                    # Should not happen if iterdir is within root, but log just in case
                    app.logger.error(f"Error calculating relative path for {item}: {e}")

            # Return the requested path relative to the root as well
            display_path = str(full_path.relative_to(absolute_root_path)).replace(
                os.sep, "/"
            )
            # Handle root case explicitly
            if display_path == ".":
                display_path = "/"
            elif not display_path.startswith("/"):
                display_path = "/" + display_path

            app.logger.debug(f"Successfully listed items for: {display_path}")
            return jsonify({"path": display_path, "items": items}), 200

        except Exception as e:
            app.logger.error(
                f"Unexpected error in list_filesystem for path '{requested_path_str}': {e}",
                exc_info=True,
            )
            return jsonify({"message": "An internal server error occurred."}), 500

    # TODO: Add /api/filesystem/read and /api/filesystem/write endpoints
