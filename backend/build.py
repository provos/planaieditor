import os
import pathlib
import shutil

# Base directory of the backend package (where pyproject.toml is)
base_dir = pathlib.Path(__file__).parent
# Source directory for frontend build assets
frontend_build_dir = base_dir.parent / "frontend" / "build"
# Target directory within the Python package source tree
target_static_dir = base_dir / "planaieditor" / "static_frontend"

print("--- Running build.py --- CWD:", os.getcwd())
print(f"Base dir: {base_dir.resolve()}")
print(f"Frontend source: {frontend_build_dir.resolve()}")
print(f"Target static dir: {target_static_dir.resolve()}")

# Ensure the target directory parent exists (it should, it's the package dir)
target_static_dir.parent.mkdir(parents=True, exist_ok=True)

if frontend_build_dir.exists() and frontend_build_dir.is_dir():
    print(f"Copying frontend build from {frontend_build_dir} to {target_static_dir}")
    # Remove existing target directory if it exists
    if target_static_dir.exists():
        print(f"Removing existing target directory: {target_static_dir}")
        shutil.rmtree(target_static_dir)
    # Copy the new build
    shutil.copytree(frontend_build_dir, target_static_dir)
    print("Frontend assets copied successfully.")
else:
    print(
        f"WARNING: Frontend build directory not found at {frontend_build_dir}. Skipping copy. The package might not contain the UI."
    )
    # If the frontend is absolutely mandatory, you might want to raise an error:
    # raise FileNotFoundError(f"Required frontend build directory not found: {frontend_build_dir}")

print("--- Finished build.py ---")
