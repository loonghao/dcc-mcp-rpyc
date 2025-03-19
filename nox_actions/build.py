"""Build the package."""

# Import built-in modules


def build(session):
    """Build the package using poetry."""
    session.install("poetry")
    session.run("poetry", "build")
