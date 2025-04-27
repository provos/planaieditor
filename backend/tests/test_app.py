import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

# Import the function to test
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import discover_python_environments, parse_traceback


class TestDiscoverPythonEnvironments(unittest.TestCase):
    """Tests for the discover_python_environments function."""

    @patch("app.Path")
    @patch("app.sys")
    @patch("app.os")
    def test_discover_python_environments_base_case(self, mock_os, mock_sys, mock_path):
        """Test basic functionality of discover_python_environments."""
        # Set up sys.executable mock
        mock_sys.executable = "/usr/bin/python3"
        mock_sys.platform = "linux"

        # Set up base_dir mock
        mock_base_dir = MagicMock()
        mock_path.return_value.parent.parent.parent = mock_base_dir

        # Mock no venvs found in base_dir
        mock_base_dir.glob.return_value = []

        # Mock os.path.isfile and os.access to say executable is valid
        mock_os.path.isfile.return_value = True
        mock_os.access.return_value = True

        # Run the function
        envs = discover_python_environments(sort_venv_paths=False)

        # Verify the current executable is included
        self.assertEqual(1, len(envs))
        self.assertEqual("/usr/bin/python3", envs[0]["path"])

        # Verify that glob was called to search for venvs
        mock_base_dir.glob.assert_called_once_with("*/.venv")

    @patch("app.Path")
    @patch("app.sys")
    @patch("app.os")
    def test_discover_python_environments_with_venvs(
        self, mock_os, mock_sys, mock_path
    ):
        """Test discovery of virtual environments in base directory."""
        # Set up sys.executable mock as a string
        mock_sys.executable = "/usr/bin/python3"
        mock_sys.platform = "linux"

        # Create real Path objects for the venv Python executables
        venv1_python = Path("/path/to/project1/.venv/bin/python")
        venv2_python = Path("/path/to/project2/.venv/bin/python")

        # Set up mock for base_dir
        mock_base_dir = MagicMock()
        mock_path.return_value.parent.parent.parent = mock_base_dir

        # Create mock venv path objects
        mock_venv1 = MagicMock()
        mock_venv1.is_dir.return_value = True
        # Return the real path object when bin/python is accessed
        mock_venv1.__truediv__.return_value.__truediv__.return_value = venv1_python

        mock_venv2 = MagicMock()
        mock_venv2.is_dir.return_value = True
        # Return the real path object when bin/python is accessed
        mock_venv2.__truediv__.return_value.__truediv__.return_value = venv2_python

        # Mock glob to return our mock venvs
        mock_base_dir.glob.return_value = [mock_venv1, mock_venv2]

        # Mock os.path.isfile and os.access
        mock_os.path.isfile.return_value = True
        mock_os.access.return_value = True

        envs = discover_python_environments(sort_venv_paths=False)

        # Verify results - should include sys.executable and 2 venvs
        self.assertEqual(3, len(envs))

        # Check executable paths in results
        paths = [env["path"] for env in envs]
        self.assertIn("/usr/bin/python3", paths)
        self.assertIn(str(venv1_python), paths)
        self.assertIn(str(venv2_python), paths)

        # Check names in results
        names = [env["name"] for env in envs]
        self.assertIn("Python (planaieditor)", names)
        self.assertIn("Python (project1)", names)
        self.assertIn("Python (project2)", names)

    @patch("app.Path")
    @patch("app.sys")
    @patch("app.os")
    def test_discover_python_environments_home_venvs(
        self, mock_os, mock_sys, mock_path
    ):
        """Test discovery of virtual environments in home directory (Linux/Mac case)."""
        # Set up sys.executable mock
        mock_sys.executable = "/usr/bin/python3"
        mock_sys.platform = "linux"  # Test Linux case

        # Set up mock for base_dir (no venvs there)
        mock_base_dir = MagicMock()
        mock_base_dir.glob.return_value = []
        mock_path.return_value.parent.parent.parent = mock_base_dir

        # Create real Path objects for virtual environments
        venv_paths = {
            ".virtualenvs": [
                Path("/home/user/.virtualenvs/venv1/bin/python"),
                Path("/home/user/.virtualenvs/venv2/bin/python"),
            ],
            "venvs": [Path("/home/user/venvs/venv3/bin/python")],
            ".cache/pypoetry/virtualenvs": [
                Path("/home/user/.cache/pypoetry/virtualenvs/venv4/bin/python")
            ],
        }

        # Define which directories exist
        venv_dirs_exist = {
            ".virtualenvs": True,
            "venvs": True,
            "Envs": False,  # This directory doesn't exist
            ".cache/pypoetry/virtualenvs": True,
        }

        # Set up mock for home directory
        mock_home = MagicMock()
        mock_path.home.return_value = mock_home

        # Create directory mocks for each path
        dir_mocks = {}

        # Create mock directory objects with real Path children
        for dir_name, exists in venv_dirs_exist.items():
            dir_mock = MagicMock()
            dir_mock.exists.return_value = exists
            dir_mocks[dir_name] = dir_mock  # Store in dict for lookup

            # Only set up venvs if directory exists
            if exists and dir_name in venv_paths:
                venv_mocks = []
                for venv_path in venv_paths[dir_name]:
                    # Create a mock venv that returns the real Path parent when accessed
                    venv_name = venv_path.parent.parent.name
                    venv_mock = MagicMock()
                    type(venv_mock).name = PropertyMock(return_value=venv_name)

                    # Set up path navigation to return real Path objects
                    bin_mock = MagicMock()
                    bin_mock.__truediv__.return_value = venv_path
                    venv_mock.__truediv__.return_value = bin_mock

                    venv_mocks.append(venv_mock)

                dir_mock.iterdir.return_value = venv_mocks

        # Set up side_effect function to return the appropriate mock based on the path
        def mock_truediv(path):
            if path in dir_mocks:
                return dir_mocks[path]
            return MagicMock(exists=lambda: False)

        mock_home.__truediv__.side_effect = mock_truediv

        # Mock os.path.isfile and os.access
        mock_os.path.isfile.return_value = True
        mock_os.access.return_value = True

        # Mock path existence checks
        def mock_path_exists(path):
            return True

        def mock_path_is_file(path):
            return True

        # We need to patch these methods on the real Path objects
        with patch.object(Path, "exists", mock_path_exists):
            with patch.object(Path, "is_file", mock_path_is_file):
                envs = discover_python_environments(sort_venv_paths=False)

        # Verify results - expect 1 system executable + 4 home venvs
        self.assertEqual(5, len(envs))

        # Verify venv names are in the results
        names = [env["name"] for env in envs]
        self.assertIn("venv1", names)
        self.assertIn("venv2", names)
        self.assertIn("venv3", names)
        self.assertIn("venv4", names)

    @patch("app.Path")
    @patch("app.sys")
    @patch("app.os")
    def test_discover_python_environments_windows(self, mock_os, mock_sys, mock_path):
        """Test that home directory venvs are not checked on Windows."""
        # Set up sys.executable mock
        mock_sys.executable = "C:\\Python39\\python.exe"
        mock_sys.platform = "win32"  # Test Windows case

        # Set up mock for base_dir (no venvs there)
        mock_base_dir = MagicMock()
        mock_base_dir.glob.return_value = []
        mock_path.return_value.parent.parent.parent = mock_base_dir

        # Set up mock for home directory - should not be accessed on Windows
        mock_home = MagicMock()
        mock_path.home.return_value = mock_home

        # Mock os.path.isfile and os.access
        mock_os.path.isfile.return_value = True
        mock_os.access.return_value = True

        # Run the function
        envs = discover_python_environments(sort_venv_paths=False)

        # Should only contain sys.executable on Windows
        self.assertEqual(1, len(envs))
        self.assertEqual("C:\\Python39\\python.exe", envs[0]["path"])

        # Verify home() was not called on Windows
        mock_path.home.assert_not_called()

    @patch("app.Path")
    @patch("app.sys")
    @patch("app.os")
    def test_discover_python_environments_deduplication(
        self, mock_os, mock_sys, mock_path
    ):
        """Test that duplicate paths are filtered out."""
        # Set up sys.executable mock
        mock_sys.executable = "/usr/bin/python3"
        mock_sys.platform = "linux"

        # Create a real Path object for the Python executable
        duplicate_python_path = Path("/path/to/project1/.venv/bin/python")

        # Set up mock for base_dir
        mock_base_dir = MagicMock()
        mock_path.return_value.parent.parent.parent = mock_base_dir

        # Create mock venv path objects that both point to the same real Path
        mock_venv1 = MagicMock()
        mock_venv1.is_dir.return_value = True
        mock_venv1.__truediv__.return_value.__truediv__.return_value = (
            duplicate_python_path
        )

        mock_venv2 = MagicMock()
        mock_venv2.is_dir.return_value = True
        mock_venv2.__truediv__.return_value.__truediv__.return_value = (
            duplicate_python_path
        )

        mock_base_dir.glob.return_value = [mock_venv1, mock_venv2]

        # Mock os.path.isfile and os.access
        mock_os.path.isfile.return_value = True
        mock_os.access.return_value = True

        envs = discover_python_environments(sort_venv_paths=False)

        # Should contain sys.executable and only one of the duplicate venvs
        self.assertEqual(2, len(envs))

        # Verify paths in result
        paths = [env["path"] for env in envs]
        self.assertIn("/usr/bin/python3", paths)
        self.assertIn(str(duplicate_python_path), paths)

        # Verify each path appears only once
        self.assertEqual(1, paths.count("/usr/bin/python3"))
        self.assertEqual(1, paths.count(str(duplicate_python_path)))


# New test class for parse_traceback
class TestParseTraceback(unittest.TestCase):
    """Tests for the parse_traceback function."""

    def test_parse_traceback_valid(self):
        """Test parsing a valid traceback with a class name."""
        traceback_str = """
Traceback (most recent call last):
  File "/tmp/tmpg2bbp4sq.py", line 92, in <module>
    graph = create_graph()
  File "/tmp/tmpg2bbp4sq.py", line 85, in create_graph
    graph.add_workers(worker1, worker2)
  File "/path/to/planai/graph.py", line 100, in add_workers
    # some planai code
  File "/tmp/tmpg2bbp4sq.py", line 25, in TaskWorker1
    some_undefined_variable
NameError: name 'some_undefined_variable' is not defined
"""
        expected_result = {
            "success": False,
            "error": {
                "message": "    some_undefined_variable\nNameError: name 'some_undefined_variable' is not defined\n",
                "nodeName": "TaskWorker1",
                "fullTraceback": None,
            },
        }
        result = parse_traceback(traceback_str)
        self.assertIsNotNone(result)
        self.assertEqual(expected_result, result)

    def test_parse_traceback_no_class_name(self):
        """Test parsing a traceback without a clear class/function name in the relevant frame."""
        traceback_str = """
Traceback (most recent call last):
  File "/tmp/tmp_script.py", line 5, in <module>
    result = 1 / 0
ZeroDivisionError: division by zero
"""
        result = parse_traceback(traceback_str)
        self.assertIsNone(result, "Expected None when no class/function name is found")

    def test_parse_traceback_module_level_error(self):
        """Test parsing a traceback with an error at the module level."""
        traceback_str = """
Traceback (most recent call last):
  File "/tmp/tmp_module_error.py", line 3, in <module>
    import non_existent_module
ModuleNotFoundError: No module named 'non_existent_module'
"""
        result = parse_traceback(traceback_str)
        # Depending on the exact implementation, this might return None or extract '<module>'
        # Based on the current code, it should return None as it looks for a class name
        self.assertIsNone(
            result, "Expected None for module-level errors without class context"
        )

    def test_parse_traceback_empty_string(self):
        """Test parsing an empty string."""
        traceback_str = ""
        result = parse_traceback(traceback_str)
        self.assertIsNone(result)

    def test_parse_traceback_not_a_traceback(self):
        """Test parsing a string that isn't a traceback."""
        traceback_str = "This is just a regular error message, not a traceback."
        result = parse_traceback(traceback_str)
        self.assertIsNone(result)

    def test_parse_traceback_nested_functions(self):
        """Test parsing traceback going through nested functions within a class."""
        traceback_str = """
Traceback (most recent call last):
  File "/tmp/tmp_nested.py", line 20, in <module>
    instance.outer_method()
  File "/tmp/tmp_nested.py", line 15, in outer_method
    self.inner_method()
  File "/tmp/tmp_nested.py", line 10, in InnerClass
    print(undefined_var)
NameError: name 'undefined_var' is not defined
"""
        expected_result = {
            "success": False,
            "error": {
                "message": "    print(undefined_var)\nNameError: name 'undefined_var' is not defined\n",
                "nodeName": "InnerClass",  # Extracts the class/function where the error occurred
                "fullTraceback": None,
            },
        }
        result = parse_traceback(traceback_str)
        self.assertIsNotNone(result)
        self.assertEqual(expected_result, result)


if __name__ == "__main__":
    unittest.main()
