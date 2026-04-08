# CLEANUP TODO

## Structural issues deferred from this cleanup round

These items were intentionally **not** refactored in this round because they need broader design or real-runtime validation.

### 1. `snapshot/rpyc.py` remote script templates need real execution validation

- Multiple remote script templates use `tempfile.mktemp()` with `fd, path = ...`, which is not a valid return shape.
- The generic fallback script defines `make_minimal_png(w=w, h=h)` even though `w` and `h` are not defined in the generated script scope.
- Current tests validate response decoding, but do **not** execute the generated remote script templates end-to-end.

**Suggested follow-up**
- Replace string-template-only testing with script-content assertions plus targeted runtime validation in real DCC or a controlled script executor.
- Remove broken placeholder code paths once validated replacements exist.

### 2. `scene/rpyc.py` contains fragile DCC script templates

- Blender `get_objects` script template references `self.config.include_transforms` inside generated remote code.
- Maya `get_lights` template uses `cmds.ltos(...)`, which looks suspicious and needs runtime verification.
- Blender `get_lights` template uses `math.*` but does not import `math` in that generated script.
- These are likely correctness risks, but touching them now would be closer to bug-fixing/refactoring than safe cleanup.

**Suggested follow-up**
- Split DCC script template generation into testable helper builders.
- Add template-level unit tests that assert required imports and interpolated config values.
- Validate generated scripts in at least Maya and Blender integration paths before cleanup deletion.

### 3. `transport/websocket.py` exposes config fields that are not enforced yet

- `ping_interval`, `ping_timeout`, and `max_message_size` exist in config but are not wired into the current sync client behavior.
- `ws_url` still checks `use_ssl` dynamically even though `WebSocketTransportConfig` does not define that field.
- This is an interface consistency problem, but changing it may affect current tests and downstream expectations.

**Suggested follow-up**
- Decide whether these fields are public API or future placeholders.
- Either implement them fully or remove/deprecate them with a documented migration path.

### 4. Transport result contract is only partially normalized

- `BaseTransport.execute()` documents a dict containing at least `{"success": bool, ...}`.
- Concrete transports still differ in whether they pass through remote dicts or wrap raw results.

**Suggested follow-up**
- Define a strict transport response contract and normalize all implementations plus mocks.

### 5. Scene hierarchy semantics differ between protocols

- HTTP hierarchy depth is derived from `/` path splitting.
- RPyC hierarchy depth is derived from `|` path splitting.
- `root_name` semantics also differ by implementation.

**Suggested follow-up**
- Document and normalize hierarchy path semantics before exposing this as a stable public contract.

### 6. Remaining iteration-specific coverage files should be consolidated into stable test modules

- `tests/test_action_adapter_iter11.py`, `tests/test_coverage_iter12.py`, and `tests/test_coverage_iter13.py` are still tied to one-off coverage passes.
- The earlier `tests/snapshot/test_http_iter11.py` and `tests/transport/test_websocket_iter11.py` cases were merged into their main test modules in this cleanup round.
- The remaining files still duplicate helpers or encode line-number-driven coverage commentary that will age quickly as source files move.

**Suggested follow-up**
- Split the `action_adapter` iteration cases across `tests/test_action_adapter_coverage.py`, adapter tests, and a small package-export test module.
- Merge the surviving `iter12`/`iter13` behavior cases into the owning stable modules and drop line-number narration.
- Delete the temporary iteration files only after coverage stays stable.


### 7. `TransformMatrix.model_dump()` may be a legacy external-compatibility surface

- In-repo search found the definition in `scene/base.py` but no internal call sites.
- The method name suggests carry-over compatibility for older callers, but removing it without upstream checks could break downstream projects.

**Suggested follow-up**
- Search dependent repositories before removing or renaming it.
- If no external consumers exist, deprecate it in docs/tests and converge on a single serialization helper.

