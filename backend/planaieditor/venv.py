import os
import sys
from pathlib import Path
from typing import Dict, List


# Function to discover Python environments
def discover_python_environments(sort_venv_paths=True) -> List[Dict[str, str]]:
    """
    Discover Python interpreters available on the system.
    Returns a list of dictionaries with 'path' and 'name' keys.
    """
    environments = []

    # Current directory venvs
    base_dir = Path(os.path.abspath(__file__)).parent.parent.parent
    potential_dirs = base_dir.glob("*/.venv")
    common_venv_paths = [
        dir / "bin" / "python" for dir in potential_dirs if dir.is_dir()
    ]
    if sys.executable not in common_venv_paths:
        common_venv_paths.append(sys.executable)
    if sort_venv_paths:
        common_venv_paths.sort()

    # Add macOS/Linux specific paths
    if sys.platform != "win32":
        # Check home directory for virtual environments
        home_dir = Path.home()
        for env_dir in [".virtualenvs", "venvs", "Envs", ".cache/pypoetry/virtualenvs"]:
            venvs_dir = home_dir / env_dir
            if venvs_dir.exists():
                for venv in venvs_dir.iterdir():
                    venv_path = venv / "bin" / "python"
                    if venv_path.exists() and venv_path.is_file():
                        environments.append(
                            {
                                "path": str(venv_path),
                                "name": f"{venv.name}",
                            }
                        )

    # Add common venv paths
    for venv_path in common_venv_paths:
        if os.path.isfile(venv_path) and os.access(venv_path, os.X_OK):
            environments.append(
                {
                    "path": str(venv_path),
                    "name": f"Python ({venv_path.parent.parent.parent.name if venv_path != sys.executable else 'planaieditor'})",
                }
            )

    # Filter out all duplicate paths
    unique_environments = []
    seen = set()
    for env in environments:
        env_path = env["path"]
        if env_path not in seen:
            unique_environments.append(env)
            seen.add(env_path)

    return unique_environments
