def pytest_addoption(parser):
    parser.addoption(
        "--write-transformed-data",
        action="store_true",
        default=False,
        help="Write transformed JSON data to file for debugging",
    )
