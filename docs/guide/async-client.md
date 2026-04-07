# Async Client

DCC-MCP-IPC includes an asyncio-based client (`AsyncDCCClient`) for non-blocking operations in async MCP server frameworks.

## AsyncDCCClient

```python
import asyncio
from dcc_mcp_ipc.client.async_dcc import AsyncDCCClient


async def main():
    client = AsyncDCCClient("maya", host="localhost", port=18812)
    await client.connect()

    result = await client.call("get_scene_info")
    print(result)

    await client.disconnect()


asyncio.run(main())
```

## Concurrent Calls

```python
import asyncio
from dcc_mcp_ipc.client.async_dcc import AsyncDCCClient


async def main():
    client = AsyncDCCClient("maya", host="localhost", port=18812)
    await client.connect()

    # Run multiple calls concurrently
    results = await asyncio.gather(
        client.call("get_scene_info"),
        client.call("list_objects"),
        client.call("get_render_settings"),
    )
    print(results)

    await client.disconnect()
```

## AsyncBaseClient

`AsyncBaseClient` is the abstract base; subclass it to create DCC-specific async clients:

```python
from dcc_mcp_ipc.client.async_base import AsyncBaseClient


class MayaAsyncClient(AsyncBaseClient):
    async def create_sphere(self, radius: float = 1.0, name: str = "sphere1"):
        return await self.call("create_sphere", radius=radius, name=name)
```

## When to Use Async

Use the async client when:
- Your MCP server framework is async (e.g., `fastmcp`, `mcp[cli]` with async handlers)
- You need to make multiple concurrent DCC calls
- You want to avoid blocking the event loop during RPyC network I/O
