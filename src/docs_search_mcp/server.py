"""MCP server exposing five tools over stdio (default) or streamable HTTP."""
from __future__ import annotations

import argparse
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .notes import Notes, NotesError
from .timeconv import TimeError, convert_time as _convert_time
from .web import FetchError, fetch_url as _fetch_url

# stdio servers must never print to stdout: it carries the JSON-RPC stream.
logging.basicConfig(stream=sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("docs-search-mcp")

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
READ_ONLY_OPEN = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                                 openWorldHint=True)


def create_server(docs_dir: str | None = None, allow_private_fetch: bool | None = None) -> FastMCP:
    docs_dir = docs_dir or os.getenv("DOCS_DIR", "sample_notes")
    if allow_private_fetch is None:
        allow_private_fetch = os.getenv("ALLOW_PRIVATE_FETCH", "").lower() in ("1", "true", "yes")
    notes = Notes(docs_dir)
    log.info("notes dir=%s sections indexed=%d allow_private_fetch=%s",
             notes.root, len(notes._sections), allow_private_fetch)
    mcp = FastMCP("docs-search-mcp")

    @mcp.tool(annotations=READ_ONLY)
    def list_notes() -> list[dict]:
        """List the note files (.md/.txt) available to search, with sizes in bytes."""
        return notes.list_notes()

    @mcp.tool(annotations=READ_ONLY)
    def search_notes(query: str, limit: int = 5) -> list[dict]:
        """Keyword-search (BM25) the notes. Returns the best matching sections with a snippet.
        Use read_note afterwards to see a whole file."""
        try:
            return notes.search(query, limit)
        except NotesError as e:
            raise ValueError(str(e)) from None

    @mcp.tool(annotations=READ_ONLY)
    def read_note(path: str, max_chars: int = 20000) -> dict:
        """Read one note by its relative path as returned by list_notes / search_notes."""
        try:
            return notes.read(path, max_chars)
        except NotesError as e:
            raise ValueError(str(e)) from None

    @mcp.tool(annotations=READ_ONLY_OPEN)
    def fetch_url(url: str, max_length: int = 5000, start_index: int = 0, raw: bool = False) -> dict:
        """Fetch a public web page and return it as markdown (or raw text). Honors robots.txt and
        refuses private/internal addresses. Long pages: pass next_start_index as start_index."""
        try:
            return _fetch_url(url, max_length, start_index, raw, allow_private=allow_private_fetch)
        except FetchError as e:
            raise ValueError(str(e)) from None

    @mcp.tool(annotations=READ_ONLY)
    def convert_time(source_timezone: str, time: str, target_timezone: str,
                     date: str | None = None) -> dict:
        """Convert a 24-hour HH:MM time between IANA timezones (e.g. Europe/Warsaw -> Asia/Dubai).
        Optional date (YYYY-MM-DD) makes daylight-saving correct for that day; default is today."""
        try:
            return _convert_time(source_timezone, time, target_timezone, date)
        except TimeError as e:
            raise ValueError(str(e)) from None

    return mcp


def main() -> None:
    p = argparse.ArgumentParser(prog="docs-search-mcp", description=__doc__)
    p.add_argument("--docs-dir", help="folder of .md/.txt notes (default: $DOCS_DIR or ./sample_notes)")
    p.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    args = p.parse_args()
    try:
        server = create_server(args.docs_dir)
    except NotesError as e:
        sys.exit(f"error: {e}")
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
