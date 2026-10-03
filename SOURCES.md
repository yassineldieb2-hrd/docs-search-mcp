# Sources and attribution

## modelcontextprotocol/servers - `fetch` and `time` reference servers
Repository: https://github.com/modelcontextprotocol/servers (studied at commit `f46d957`, Sep 2026)
License: the repository is **transitioning from MIT to Apache-2.0**. The `fetch` package carries an MIT license
(Copyright (c) 2024 Anthropic, PBC) and `time` declares MIT in its `pyproject.toml`. Because per-contribution licensing is
mixed, I treat the code as MIT and keep the attribution below. This project is released under MIT (see `LICENSE`).

**What is based on them (ideas / structure, re-implemented, not copy-pasted):**
- `time`: the `convert_time` tool concept and its result shape (source/target time, day of week, DST flag, offset difference).
- `fetch`: the `fetch_url` tool concept - check `robots.txt`, convert HTML to markdown, return long pages in slices via `start_index`.
- Both: exposing read-only tools with MCP tool annotations over stdio.

**What is different (my own code):**
- Built on the high-level `FastMCP` decorator API of the official Python SDK instead of the low-level `Server` handlers.
- `search_notes` / `read_note` / `list_notes`: a new local-notes toolset (BM25 ranking over sections, path-traversal and symlink protection) - not in upstream.
- `fetch_url`: SSRF guard (blocks private, loopback and link-local addresses) re-applied on every redirect hop, response size cap, redirect limit, stdlib `robotparser` instead of `protego`, simple HTML cleanup instead of `readabilipy`.
- `convert_time`: optional `date` so DST is correct for that day, detection of non-existent and ambiguous wall-clock times around DST changes.
- Errors surface as MCP tool errors; logging goes to stderr.
- Tests, including a protocol-level test using the official MCP client.

## Other
`sample_notes/` were written by me. Dependencies (mcp SDK, httpx, markdownify, tzdata) are used as installed packages, not vendored.
