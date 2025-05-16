import logging
import os
import sys

# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def pytest_addoption(parser):
    parser.addoption(
        "--write-transformed-data",
        action="store_true",
        default=False,
        help="Write transformed JSON data to file for debugging",
    )


def pytest_configure(config):
    """Configures logging to stdout/stderr."""
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
