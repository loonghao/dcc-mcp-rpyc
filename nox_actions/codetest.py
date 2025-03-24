# Import built-in modules
import os

# Import third-party modules
import nox

# Import local modules
from nox_actions.utils import PACKAGE_NAME
from nox_actions.utils import THIS_ROOT


def pytest(session: nox.Session) -> None:
    """Run pytest with coverage.

    Args:
    ----
        session: The nox session

    Examples:
    --------
        Run all tests:
        $ nox -s pytest

        Run specific tests:
        $ nox -s pytest -- -xvs tests/test_filesystem.py::test_discover_actions_in_paths

    """
    # Install project and dependencies
    session.install(".")
    # Install testing dependencies
    session.install("pytest", "pytest_cov", "pytest_mock", "pyfakefs", "pytest-timeout", "rpyc>=6.0.0")
    test_root = os.path.join(THIS_ROOT, "tests")

    # Get any additional arguments passed after --
    pytest_args = session.posargs if session.posargs else []

    # Default arguments
    default_args = [
        f"--cov={PACKAGE_NAME}",
        "--cov-report=xml:coverage.xml",
        "--cov-report=term",
        "--timeout=30",  # set timeout to 30 seconds
        "--timeout-method=thread",  # Use thread method to handle timeout
        f"--rootdir={test_root}",
    ]

    # Run pytest with all arguments
    session.run("pytest", *default_args, *pytest_args, env={"PYTHONPATH": THIS_ROOT.as_posix()})
