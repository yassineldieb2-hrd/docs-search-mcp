"""Spawns the real server as a subprocess and talks to it with the official MCP client over stdio."""
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

NOTES = str(Path(__file__).parent.parent / "sample_notes")




def payload(result):
    assert not result.isError, result.content
    return json.loads(result.content[0].text)


async def test_tools_listed_with_read_only_annotations_and_schemas():
    async with stdio_client(StdioServerParameters(command=sys.executable, args=["-m", "docs_search_mcp", "--docs-dir", NOTES])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = {t.name: t for t in (await s.list_tools()).tools}
            assert set(tools) == {"list_notes", "search_notes", "read_note", "fetch_url", "convert_time"}
            assert all(t.annotations.readOnlyHint for t in tools.values())
            assert tools["search_notes"].inputSchema["required"] == ["query"]
            assert tools["fetch_url"].annotations.openWorldHint is True


async def test_tool_calls_end_to_end():
    async with stdio_client(StdioServerParameters(command=sys.executable, args=["-m", "docs_search_mcp", "--docs-dir", NOTES])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            hits = (await s.call_tool("search_notes", {"query": "reciprocal rank fusion"})).structuredContent
            hits = hits["result"] if isinstance(hits, dict) and "result" in hits else hits
            assert hits[0]["path"] == "rag-basics.md"
            note = payload(await s.call_tool("read_note", {"path": "rag-basics.md"}))
            assert "Hybrid search" in note["content"]
            conv = payload(await s.call_tool("convert_time", {"source_timezone": "Europe/Warsaw", "time": "10:00", "target_timezone": "Asia/Dubai", "date": "2026-07-15"}))
            assert conv["target"]["datetime"].startswith("2026-07-15T12:00")


async def test_errors_are_tool_errors_not_crashes():
    async with stdio_client(StdioServerParameters(command=sys.executable, args=["-m", "docs_search_mcp", "--docs-dir", NOTES])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            bad = await s.call_tool("read_note", {"path": "../../etc/passwd"})
            assert bad.isError and "outside" in bad.content[0].text
            bad = await s.call_tool("fetch_url", {"url": "http://169.254.169.254/latest/meta-data/"})
            assert bad.isError and "non-public" in bad.content[0].text
            bad = await s.call_tool("convert_time", {"source_timezone": "Mars/Base", "time": "10:00", "target_timezone": "UTC"})
            assert bad.isError
            # server still alive after errors
            assert not (await s.call_tool("list_notes", {})).isError
