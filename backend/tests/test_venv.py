import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

from planaieditor.venv import discover_python_environments


class TestDiscoverPythonEnvironments(unittest.TestCase):
    """Tests for the discover_python_environments function."""

    def _setup_path_mocks(
        self, mock_path_class, mock_os, sys_executable_path, base_dir_mock=None
    ):
        """
        Helper method to set up common Path and os mocks.

        Args:
            mock_path_class: Mocked Path class
            mock_os: Mocked os module
            sys_executable_path: Path string for sys.executable
            base_dir_mock: Optional base directory mock to use

        Returns:
            tuple: (mock_sys_exec_path, mock_file_path, mock_base_dir)
        """
        # Set up mock for base_dir - needs 4 parents
        mock_file_path = MagicMock()
        if base_dir_mock is None:
            mock_base_dir = MagicMock()
            mock_base_dir.glob.return_value = []
        else:
            mock_base_dir = base_dir_mock
        mock_file_path.parent.parent.parent.parent = mock_base_dir

        # Mock sys.executable Path object
        mock_sys_exec_path = MagicMock()
        mock_sys_exec_path.__str__.return_value = sys_executable_path
        mock_sys_exec_path.parent.parent.parent.name = "planaieditor"

        # Make sure sys.executable Path is not equal to other venv paths
        mock_sys_exec_path.__eq__ = lambda self, other: False
        mock_sys_exec_path.__ne__ = lambda self, other: True

        # Set up Path constructor to return appropriate mocks
        def path_constructor_side_effect(*args, **kwargs):
            if len(args) > 0:
                if args[0] == sys_executable_path:
                    return mock_sys_exec_path
                elif "/__file__" in str(args[0]) or args[0].endswith("venv.py"):
                    return mock_file_path
            return MagicMock()

        mock_path_class.side_effect = path_constructor_side_effect

        # Mock os.path.abspath to return a recognizable path
        mock_os.path.abspath.return_value = "/some/path/to/venv.py/__file__"

        return mock_sys_exec_path, mock_file_path, mock_base_dir

    @patch("planaieditor.venv.os")
    @patch("planaieditor.venv.sys")
    @patch("planaieditor.venv.Path")
    def test_discover_python_environments_base_case(
        self, mock_path_class, mock_sys, mock_os
    ):
        """Test basic functionality of discover_python_environments."""
        # Set up sys.executable mock
        mock_sys.executable = "/usr/bin/python3"
        mock_sys.platform = "linux"

        # Set up mocks using helper
        _, _, mock_base_dir = self._setup_path_mocks(
            mock_path_class, mock_os, "/usr/bin/python3"
        )

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

    @patch("planaieditor.venv.os")
    @patch("planaieditor.venv.sys")
    @patch("planaieditor.venv.Path")
    def test_discover_python_environments_with_venvs(
        self, mock_path_class, mock_sys, mock_os
    ):
        """Test discovery of virtual environments in base directory."""
        # Set up sys.executable mock as a string
        mock_sys.executable = "/usr/bin/python3"
        mock_sys.platform = "linux"

        # Create real Path objects for the venv Python executables
        venv1_python = Path("/path/to/project1/.venv/bin/python")
        venv2_python = Path("/path/to/project2/.venv/bin/python")

        # Create mock venv path objects
        mock_venv1 = MagicMock()
        mock_venv1.is_dir.return_value = True
        # Return the real path object when bin/python is accessed
        mock_venv1.__truediv__.return_value.__truediv__.return_value = venv1_python

        mock_venv2 = MagicMock()
        mock_venv2.is_dir.return_value = True
        # Return the real path object when bin/python is accessed
        mock_venv2.__truediv__.return_value.__truediv__.return_value = venv2_python

        # Create base dir mock with venvs
        mock_base_dir = MagicMock()
        mock_base_dir.glob.return_value = [mock_venv1, mock_venv2]

        # Set up mocks using helper
        self._setup_path_mocks(
            mock_path_class, mock_os, "/usr/bin/python3", mock_base_dir
        )

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

    @patch("planaieditor.venv.Path")
    @patch("planaieditor.venv.sys")
    @patch("planaieditor.venv.os")
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
        mock_path.return_value.parent.parent.parent.parent = mock_base_dir

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

    @patch("planaieditor.venv.os")
    @patch("planaieditor.venv.sys")
    @patch("planaieditor.venv.Path")
    def test_discover_python_environments_windows(
        self, mock_path_class, mock_sys, mock_os
    ):
        """Test that home directory venvs are not checked on Windows."""
        # Set up sys.executable mock
        mock_sys.executable = "C:\\Python39\\python.exe"
        mock_sys.platform = "win32"  # Test Windows case

        # Set up mocks using helper
        self._setup_path_mocks(mock_path_class, mock_os, "C:\\Python39\\python.exe")

        # Set up mock for home directory - should not be accessed on Windows
        mock_home = MagicMock()
        mock_path_class.home.return_value = mock_home

        # Mock os.path.isfile and os.access
        mock_os.path.isfile.return_value = True
        mock_os.access.return_value = True

        # Run the function
        envs = discover_python_environments(sort_venv_paths=False)

        # Should only contain sys.executable on Windows
        self.assertEqual(1, len(envs))
        self.assertEqual("C:\\Python39\\python.exe", envs[0]["path"])

        # Verify home() was not called on Windows
        mock_path_class.home.assert_not_called()

    @patch("planaieditor.venv.os")
    @patch("planaieditor.venv.sys")
    @patch("planaieditor.venv.Path")
    def test_discover_python_environments_deduplication(
        self, mock_path_class, mock_sys, mock_os
    ):
        """Test that duplicate paths are filtered out."""
        # Set up sys.executable mock
        mock_sys.executable = "/usr/bin/python3"
        mock_sys.platform = "linux"

        # Create a real Path object for the Python executable
        duplicate_python_path = Path("/path/to/project1/.venv/bin/python")

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

        # Create base dir mock with duplicate venvs
        mock_base_dir = MagicMock()
        mock_base_dir.glob.return_value = [mock_venv1, mock_venv2]

        # Set up mocks using helper
        self._setup_path_mocks(
            mock_path_class, mock_os, "/usr/bin/python3", mock_base_dir
        )

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


if __name__ == "__main__":
    unittest.main()
