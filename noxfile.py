# Import built-in modules
import os
import sys

# Import third-party modules
import nox

ROOT = os.path.dirname(__file__)

# Ensure maya_umbrella is importable.
if ROOT not in sys.path:
    sys.path.append(ROOT)

# Import local modules
from nox_actions import build
from nox_actions import codetest
from nox_actions import docs
from nox_actions import lint

nox.session(lint.lint, name="lint")
nox.session(lint.lint_fix, name="lint-fix")
nox.session(codetest.pytest, name="pytest")
nox.session(docs.docs, name="docs")
nox.session(docs.docs_serve, name="docs-serve")
nox.session(build.build, name="build")
