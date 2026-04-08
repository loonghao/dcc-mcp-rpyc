# Contributing to dcc-mcp-ipc

Thank you for your interest in improving `dcc-mcp-ipc`.
This repository provides the shared IPC adapter layer used by DCC + MCP integrations, so changes should keep the codebase easy to understand, test, and maintain.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/loonghao/dcc-mcp-ipc.git
   cd dcc-mcp-ipc
   ```

2. Install development dependencies:
   ```bash
   poetry install
   ```

   If you prefer a plain pip-based environment, `requirements-dev.txt` includes the tools used in CI and local verification.

## Code Quality Commands

The main verification entry points are the configured `nox` sessions:

```bash
nox -s lint
nox -s pytest
```

For local cleanup before submitting a PR, these direct commands are also useful:

```bash
ruff format src tests
ruff check src tests
mypy src/dcc_mcp_ipc
pytest tests/
```

## Code Style Expectations

This project uses:
- [Ruff](https://github.com/astral-sh/ruff) for formatting and linting
- [mypy](https://mypy.readthedocs.io/) for type checking
- [isort](https://pycqa.github.io/isort/) in `nox` automation and repo maintenance flows

Please keep changes focused, avoid unrelated refactors, and update tests/docs whenever behavior or public APIs change.

## Pull Request Process

1. Create a topic branch from `main`.
2. Keep the change set focused and explain the motivation in the PR description.
3. Run the relevant checks before submitting (`nox -s lint` and `nox -s pytest` at minimum).
4. Update documentation when public APIs, examples, or workflows change.
5. Use Conventional Commits for commit messages.

## Commit Messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>[optional scope]: <description>
```

Common types include:
- `feat`: a new feature
- `fix`: a bug fix
- `docs`: documentation changes
- `refactor`: code restructuring without feature changes
- `test`: test additions or updates
- `chore`: maintenance and cleanup tasks

Examples:
- `docs(transport): align factory examples with current API`
- `chore(cleanup): tests: remove debug output from rpyc service checks`

## License

By contributing to this project, you agree that your contributions are licensed under the [MIT License](LICENSE).

