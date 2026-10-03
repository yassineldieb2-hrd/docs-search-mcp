"""Minimal MCP client: starts the server over stdio and calls every tool.
Run from the repo root after `pip install -e .`:   python examples/client_demo.py
"""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    params = StdioServerParameters(command=sys.executable,
                                   args=["-m", "docs_search_mcp", "--docs-dir", "sample_notes"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("tools:", [t.name for t in (await session.list_tools()).tools])
            calls = [
                ("list_notes", {}),
                ("search_notes", {"query": "stdio logs stdout"}),
                ("convert_time", {"source_timezone": "Europe/Warsaw", "time": "10:00",
                                  "target_timezone": "Asia/Dubai", "date": "2026-07-15"}),
            ]
            for name, args in calls:
                result = await session.call_tool(name, args)
                print(f"\n{name}({args}) ->")
                for block in result.content:
                    print(block.text)


asyncio.run(main())
