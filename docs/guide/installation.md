# Installation

## Requirements

| Dependency | Version | Notes |
|------------|---------|-------|
| Python | >= 3.8, < 4.0 | |
| dcc-mcp-core | >= 0.12.0, < 1.0.0 | Rust/PyO3 backend — installed automatically |
| rpyc | >= 6.0.0, < 7.0.0 | Remote Python Call transport |
| zeroconf | >= 0.38.0 | *Optional* — for mDNS service discovery |

## Install from PyPI

```bash
pip install dcc-mcp-ipc
```

### With ZeroConf support

ZeroConf enables automatic mDNS-based service discovery so clients can find DCC servers without manual configuration:

```bash
pip install "dcc-mcp-ipc[zeroconf]"
```

## Install with Poetry

```bash
poetry add dcc-mcp-ipc
```

With ZeroConf:

```bash
poetry add "dcc-mcp-ipc[zeroconf]"
```

## Development Installation

```bash
git clone https://github.com/loonghao/dcc-mcp-ipc.git
cd dcc-mcp-ipc
poetry install
```

This installs the package in editable mode along with all development dependencies.

## Verify Installation

```python
import dcc_mcp_ipc
print(dir(dcc_mcp_ipc))
```

You should see the public API surface including `ActionAdapter`, `DCCServer`, `BaseDCCClient`, `SkillManager`, etc.
