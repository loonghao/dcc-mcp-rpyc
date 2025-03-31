# Import third-party modules
import nox


def lint(session: nox.Session) -> None:
    session.install("isort", "ruff")
    session.run("isort", "--check-only", "src", "tests", "nox_actions")
    session.run("ruff", "check")


def lint_fix(session: nox.Session) -> None:
    session.install("isort", "ruff", "pre-commit", "autoflake")
    session.run("ruff", "format", ".")
    session.run("ruff", "check", "--fix", "--unsafe-fixes", success_codes=[0, 1])
    session.run("isort", "src", "tests", "nox_actions")
    session.run(
        "autoflake",
        "--in-place",
        "--recursive",
        "--remove-all-unused-imports",
        "--remove-unused-variables",
        "--expand-star-imports",
        "--exclude",
        "__init__.py",
        "src",
        "tests",
        "nox_actions",
    )
