"""Nox sessions for building documentation."""

# Import built-in modules
import os
import shutil

# Import local modules
from nox_actions.utils import PACKAGE_NAME
from nox_actions.utils import THIS_ROOT


def docs(session):
    """Build the documentation."""
    output_dir = os.path.join(THIS_ROOT, "docs", "build", "html")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    session.install("-e", ".")
    session.install("sphinx", "sphinx-rtd-theme", "myst-parser")
    session.chdir(os.path.join(THIS_ROOT, "docs"))
    session.run(
        "sphinx-build",
        "-b",
        "html",
        "source",
        "build/html",
        "-W",
    )


def docs_serve(session):
    """Build and serve the documentation with live reloading on file changes."""
    session.install("-e", ".")
    session.install("sphinx", "sphinx-rtd-theme", "sphinx-autobuild", "myst-parser")
    session.chdir(os.path.join(THIS_ROOT, "docs"))
    session.run(
        "sphinx-autobuild",
        "--watch",
        f"../src/{PACKAGE_NAME}",
        "--re-ignore",
        r"_build/.*",
        "--open-browser",
        "source",
        "build/html",
    )
