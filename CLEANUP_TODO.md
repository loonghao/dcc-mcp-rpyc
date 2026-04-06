## Cleanup TODO

### Structural debt confirmed on `auto-improve`
- `src/dcc_mcp_ipc/scene/http.py` (`538` lines), `src/dcc_mcp_ipc/scene/rpyc.py` (`601` lines), and `src/dcc_mcp_ipc/transport/websocket.py` (`555` lines) exceed the preferred module size threshold; split points should be planned instead of refactoring blindly during hygiene passes.
- `src/dcc_mcp_ipc/transport/factory.py` still accepts `**kwargs` that are not applied to transport config creation or cache identity; callers must build explicit config objects until the contract is redesigned.
- `src/dcc_mcp_ipc/scene/rpyc.py` and `src/dcc_mcp_ipc/snapshot/__init__.py` still expose direct `execute_func` / `conn.root.execute_python` style usage instead of clearly routing through the transport abstraction.
- `src/dcc_mcp_ipc/scene/http.py` and `src/dcc_mcp_ipc/snapshot/http.py` duplicate HTTP session / timeout / error-handling concerns that overlap with `src/dcc_mcp_ipc/transport/http.py`; extract or centralize only in a dedicated refactor.
- Optional dependency policy is still unclear: `websockets` and `requests` are treated as optional in code/tests, while `pyproject.toml` still requires `rpyc` unconditionally and does not document transport-specific extras.

### Test debt confirmed on `auto-improve`
- `tests/scene/test_http.py`, `tests/scene/test_rpyc.py`, and `tests/transport/test_websocket.py` are already large enough that shared lifecycle assertions should be consolidated before adding more protocol cases.
- HTTP snapshot tests still rely on optional `requests` availability and skip markers; clarify the supported CI dependency matrix before removing more compatibility branches.
