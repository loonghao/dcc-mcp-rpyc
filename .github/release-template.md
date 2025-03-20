# dcc-mcp-rpyc $RELEASE_VERSION

<div align="center">

[![PyPI version](https://badge.fury.io/py/dcc-mcp-rpyc.svg)](https://badge.fury.io/py/dcc-mcp-rpyc)
[![Build Status](https://github.com/loonghao/dcc-mcp-rpyc/workflows/Build%20and%20Release/badge.svg)](https://github.com/loonghao/dcc-mcp-rpyc/actions)
[![Documentation Status](https://readthedocs.org/projects/dcc-mcp-rpyc/badge/?version=latest)](https://dcc-mcp-rpyc.readthedocs.io/en/latest/?badge=latest)
[![Python Version](https://img.shields.io/pypi/pyversions/dcc-mcp-rpyc.svg)](https://pypi.org/project/dcc-mcp-rpyc/)
[![License](https://img.shields.io/github/license/loonghao/dcc-mcp-rpyc.svg)](https://github.com/loonghao/dcc-mcp-rpyc/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/dcc-mcp-rpyc)](https://pepy.tech/project/dcc-mcp-rpyc)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/ruff-enabled-brightgreen)](https://github.com/astral-sh/ruff)

</div>

## 🚀 What's New

$CHANGES

For detailed release notes, see the [CHANGELOG.md](https://github.com/loonghao/dcc-mcp-rpyc/blob/main/CHANGELOG.md).

## 📦 Installation

### Using pip

```bash
pip install dcc-mcp-rpyc==$RELEASE_VERSION
```

### Using Poetry

```bash
poetry add dcc-mcp-rpyc==$RELEASE_VERSION
```

### From source

```bash
git clone https://github.com/loonghao/dcc-mcp-rpyc.git
cd dcc-mcp-rpyc
git checkout $RELEASE_VERSION  # Checkout the specific version
pip install -e .
```

## 💻 Supported Platforms

- Windows
- Linux
- macOS

## 🐍 Python Compatibility

- Python 3.7+

## ✨ Key Features

- Thread-safe RPYC server implementation for DCC applications
- Service discovery for finding DCC services on the network
- Abstract base classes for creating DCC-specific adapters and services
- Support for multiple DCC applications (Maya, Houdini, 3ds Max, Nuke, etc.)
- Integration with the Model Context Protocol (MCP) for AI-driven DCC control
- Connection pooling for efficient resource management
- Transparent remote execution of DCC commands
- Native API access without translation layers

## 📚 Documentation

For detailed documentation, visit [https://dcc-mcp-rpyc.readthedocs.io/](https://dcc-mcp-rpyc.readthedocs.io/)
