# auto-improve Automation Memory

## Iteration 10 — 2026-04-08

**Commit**: `79279d6` — pushed to `origin/auto-improve`

**Coverage**: 96% (134 missing) → 96% (114 missing, -20 lines)
**Tests**: 1068 → 1111 passed (+43 new), 4 skipped

### Changes Made
1. **`tests/scene/test_http.py`**: Added 7 new test classes covering:
   - `TestNonUnrealPaths`: get_materials/cameras/lights/selection/metadata all return `[]` for non-unreal DCC (lines 118,124,130,150,171)
   - `TestSceneNameRawResponse`: `_get_scene_name` with raw dict response + graceful failure
   - `TestUnrealGetObjectsEdgeCases`: non-dict response and non-list actors in `_unreal_get_objects` (lines 214,218)
   - `TestUnrealCamerasExceptionFallback`: FOV query raises → default 90.0 used (lines 310-311)
   - `TestUnrealLightsEdgeCases`: non-list components and intensity/color exception (lines 347,379-380)
   - `TestActorTransformDisabled`: `include_transforms=False`, success, and failure paths (line 456→458)
   - `scene/http.py`: 91% → **99%**

2. **`tests/scene/test_rpyc.py`**: Added 6 new test classes covering:
   - `TestGetExecFuncNoRoot`: connection.root=None raises SceneError
   - `TestRpycGetHierarchyEdgeCases`: non-dict raw → fallback to objects, SceneError → fallback
   - `TestRpycQueryNonListRaw`: materials/cameras/lights return non-list → `[]` fallback
   - `TestRpycSelectionGenericFallback`: selection SceneError/TypeError → generic path
   - `TestBlenderMetadataEdgeCases`: SceneError and other-DCC metadata paths
   - `scene/rpyc.py`: 93% → **97%**

3. **`tests/server/test_server_decorators.py`** (new): Full coverage of `with_environment_info`,
   `with_scene_info`, `with_session_info` (line 74) — `server/decorators.py`: 92% → **100%**

4. **`tests/server/test_server_lifecycle.py`**: Added `TestServerThreadErrorPath` covering the
   `_server_thread` exception path (lines 145-147) — `server/lifecycle.py`: 94% → **97%**

5. **`tests/snapshot/test_http.py`**: Added `TestHTTPHealthCheckFallback` covering the
   health_check fallback to root URL when /health raises (line 271) — `snapshot/http.py`: 93% → 94%

### Remaining Low-Coverage Areas (for next iteration)
- `scene/http.py` 99% — lines 18-19 (REQUESTS_AVAILABLE=False import fallback), 295->299 (camera prop query format)
- `scene/rpyc.py` 97% — lines 431-432 (SceneError in blender), 450-529 various script fallback branches
- `snapshot/http.py` 94% — lines 28-31 (requests unavailable fallback), 153->163, 157->159 (error key paths)
- `transport/websocket.py` 94% — reconnect/error paths
- `transport/rpyc_transport.py` 95% — execute_python/call_function/import_module not-connected paths

### Next Iteration Priorities
1. Cover `snapshot/http.py` lines 153->163 (ReturnValue is str, error key) — need precise mock path
2. Cover `scene/rpyc.py` remaining branches (script fallback inner except clauses)
3. Cover `transport/rpyc_transport.py` 95% — not-connected error paths (lines 215-216, 242-243, 263-264)
4. Cover `transport/websocket.py` reader loop error and reconnect paths
5. Check upstream `dcc-mcp-core` for new API changes
