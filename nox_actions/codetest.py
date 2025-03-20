# Import built-in modules
import os

# Import third-party modules
import nox

# Import local modules
from nox_actions.utils import PACKAGE_NAME
from nox_actions.utils import THIS_ROOT


def pytest(session: nox.Session) -> None:
    session.install(".")
    session.install("pytest", "pytest_cov", "pytest_mock", "pyfakefs", "pytest-timeout")
    test_root = os.path.join(THIS_ROOT, "tests")
    session.run(
        "pytest",
        f"--cov={PACKAGE_NAME}",
        "--cov-report=xml:coverage.xml",
        f"--rootdir={test_root}",
        "--timeout=10",  # Set global timeout to 10 seconds
        "--timeout-method=thread",  # Use thread method to handle timeout
        env={"PYTHONPATH": THIS_ROOT.as_posix()},
    )
