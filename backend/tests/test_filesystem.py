import json

import pytest
from flask import Flask
from planaieditor.filesystem import sanitize_path, setup_filesystem


@pytest.fixture
def app():
    """Create a Flask application for testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def test_dir(tmp_path):
    """Create a temporary directory with test files and subdirectories."""
    # Root directory
    root = tmp_path / "test_root"
    root.mkdir()

    # Subdirectory 1 with files
    subdir1 = root / "subdir1"
    subdir1.mkdir()
    (subdir1 / "file1.txt").write_text("File 1 content")
    (subdir1 / "file2.txt").write_text("File 2 content")
    (subdir1 / "file3.exe").write_text("File 3 content")  # should never be listed

    # Subdirectory 2 (empty)
    subdir2 = root / "subdir2"
    subdir2.mkdir()

    # A file in the root
    (root / "root_file.txt").write_text("Root file content")

    return root


class TestSanitizePath:
    """Tests for the sanitize_path function."""

    def test_valid_paths(self, test_dir):
        """Test sanitize_path with valid paths."""
        cases = [
            (".", test_dir),
            ("/", test_dir),
            ("subdir1", test_dir / "subdir1"),
            ("/subdir1", test_dir / "subdir1"),
            ("subdir1/file1.txt", test_dir / "subdir1" / "file1.txt"),
        ]

        for input_path, expected_path in cases:
            result = sanitize_path(test_dir, input_path)
            assert result.resolve() == expected_path.resolve()

    def test_traversal_attempts(self, test_dir):
        """Test sanitize_path protects against path traversal attempts."""
        traversal_cases = [
            "../",
            "../../",
            "subdir1/../../",
            "/subdir1/../..",
            "subdir1/../subdir2/../..",
        ]

        for case in traversal_cases:
            with pytest.raises(ValueError, match="Attempt to access path outside root"):
                sanitize_path(test_dir, case)


class TestListFilesystem:
    """Tests for the list_filesystem endpoint."""

    def test_list_root(self, app, test_dir):
        """Test listing the root directory."""
        # Setup the filesystem routes
        setup_filesystem(app, test_dir)

        # Make a request to list the root
        with app.test_client() as client:
            response = client.get("/api/filesystem/list?path=/")

            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["path"] == "/"
            assert len(data["items"]) == 3  # root_file.txt, subdir1, subdir2

            # Verify items contain expected fields
            for item in data["items"]:
                assert "name" in item
                assert "type" in item
                assert "path" in item

            # Verify specific items exist (paths should have leading slashes now)
            item_paths = [item["path"] for item in data["items"]]
            assert "/root_file.txt" in item_paths
            assert "/subdir1" in item_paths
            assert "/subdir2" in item_paths

    def test_list_subdirectory(self, app, test_dir):
        """Test listing a subdirectory."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.get("/api/filesystem/list?path=/subdir1")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["path"] == "/subdir1"

            # Should contain 2 files
            assert len(data["items"]) == 2
            file_names = [item["name"] for item in data["items"]]
            assert "file1.txt" in file_names
            assert "file2.txt" in file_names

            # Paths should have leading slash and include directory
            file_paths = [item["path"] for item in data["items"]]
            assert "/subdir1/file1.txt" in file_paths
            assert "/subdir1/file2.txt" in file_paths

    def test_list_nonexistent_directory(self, app, test_dir):
        """Test listing a directory that doesn't exist."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.get("/api/filesystem/list?path=/nonexistent")

            assert response.status_code == 404
            data = json.loads(response.data)
            assert "message" in data

    def test_list_file_path(self, app, test_dir):
        """Test attempting to list a file (should fail)."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.get("/api/filesystem/list?path=/root_file.txt")

            assert response.status_code == 400
            data = json.loads(response.data)
            assert "message" in data

    def test_list_traversal_attempt(self, app, test_dir):
        """Test path traversal protection in list_filesystem."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.get("/api/filesystem/list?path=/../")

            # Should now return 403 instead of 500
            assert response.status_code == 403
            data = json.loads(response.data)
            assert "message" in data
            assert "Access denied" in data["message"]


class TestReadFilesystem:
    """Tests for the read_filesystem endpoint."""

    def test_read_valid_file(self, app, test_dir):
        """Test reading a valid file."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.get("/api/filesystem/read?path=/root_file.txt")

            assert response.status_code == 200
            assert response.data == b"Root file content"

    def test_read_missing_path(self, app, test_dir):
        """Test read without a path parameter."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.get("/api/filesystem/read")

            assert response.status_code == 400
            data = json.loads(response.data)
            assert "message" in data

    def test_read_nonexistent_file(self, app, test_dir):
        """Test reading a nonexistent file."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.get("/api/filesystem/read?path=/nonexistent.txt")

            assert response.status_code == 404
            data = json.loads(response.data)
            assert "message" in data

    def test_read_directory(self, app, test_dir):
        """Test attempting to read a directory (should fail)."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.get("/api/filesystem/read?path=/subdir1")

            assert response.status_code == 400
            data = json.loads(response.data)
            assert "message" in data

    def test_read_traversal_attempt(self, app, test_dir):
        """Test path traversal protection in read_filesystem."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.get("/api/filesystem/read?path=/../outside.txt")

            assert response.status_code == 403
            data = json.loads(response.data)
            assert "message" in data

    def test_read_disallowed_extension(self, app, test_dir):
        """Test reading a file with a disallowed extension."""
        setup_filesystem(app, test_dir)

        # Create a file with disallowed extension
        disallowed_file = test_dir / "test.exe"
        disallowed_file.write_text("Test content")

        with app.test_client() as client:
            response = client.get("/api/filesystem/read?path=/test.exe")

            assert response.status_code == 400
            data = json.loads(response.data)
            assert "message" in data
            assert "disallowed extension" in data["message"].lower()


class TestWriteFilesystem:
    """Tests for the write_filesystem endpoint."""

    def test_write_new_file(self, app, test_dir):
        """Test writing to a new file."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.post(
                "/api/filesystem/write",
                json={"path": "/new_file.txt", "content": "New file content"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "message" in data
            assert data["path"] == "/new_file.txt"

            # Verify file was actually written
            file_path = test_dir / "new_file.txt"
            assert file_path.exists()
            assert file_path.read_text() == "New file content"

    def test_overwrite_existing_file(self, app, test_dir):
        """Test overwriting an existing file."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.post(
                "/api/filesystem/write",
                json={"path": "/root_file.txt", "content": "Updated content"},
            )

            assert response.status_code == 200

            # Verify file was updated
            file_path = test_dir / "root_file.txt"
            assert file_path.read_text() == "Updated content"

    def test_write_missing_parameters(self, app, test_dir):
        """Test write with missing parameters."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            # Missing path
            response1 = client.post(
                "/api/filesystem/write", json={"content": "Content only"}
            )
            assert response1.status_code == 400

            # Missing content
            response2 = client.post(
                "/api/filesystem/write", json={"path": "/some_file.txt"}
            )
            assert response2.status_code == 400

    def test_write_to_nonexistent_directory(self, app, test_dir):
        """Test writing to a file in a directory that doesn't exist."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.post(
                "/api/filesystem/write",
                json={"path": "/nonexistent_dir/file.txt", "content": "Content"},
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert "message" in data

    def test_write_traversal_attempt(self, app, test_dir):
        """Test path traversal protection in write_filesystem."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.post(
                "/api/filesystem/write",
                json={"path": "/../outside.txt", "content": "Malicious content"},
            )

            assert response.status_code == 403
            data = json.loads(response.data)
            assert "message" in data

            # Verify file was not created outside root
            outside_path = test_dir.parent / "outside.txt"
            assert not outside_path.exists()

    def test_write_disallowed_extension(self, app, test_dir):
        """Test writing a file with a disallowed extension."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.post(
                "/api/filesystem/write",
                json={"path": "/test.exe", "content": "Test content"},
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert "message" in data
            assert "disallowed extension" in data["message"].lower()

            # Verify file was not created
            assert not (test_dir / "test.exe").exists()

    def test_write_allowed_extension(self, app, test_dir):
        """Test writing a file with an allowed extension."""
        setup_filesystem(app, test_dir)

        with app.test_client() as client:
            response = client.post(
                "/api/filesystem/write",
                json={"path": "/test.py", "content": "print('Hello')"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "message" in data
            assert data["path"] == "/test.py"

            # Verify file was created with correct content
            file_path = test_dir / "test.py"
            assert file_path.exists()
            assert file_path.read_text() == "print('Hello')"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
