# Attribution

## modelcontextprotocol/servers - `fetch` and `time` reference servers
https://github.com/modelcontextprotocol/servers (reviewed at commit `f46d957`, Sep 2026).
The repository is transitioning from MIT to Apache-2.0: the `fetch` package carries an MIT license (Copyright (c) 2024 Anthropic, PBC)
and `time` declares MIT in its `pyproject.toml`. Because per-contribution licensing is mixed, the code is treated as MIT and the
attribution is kept here. This project is released under MIT (see `LICENSE`).

The `convert_time` tool concept and result shape (source and target time, day of week, DST flag, offset difference) and the
`fetch_url` tool concept (check robots.txt, convert HTML to markdown, return long pages in slices via `start_index`) follow the
upstream servers. The implementation here is separate and differs as follows:
- built on the high-level `FastMCP` decorator API of the official Python SDK instead of the low-level `Server` handlers
- a local-notes toolset (`search_notes`, `read_note`, `list_notes`) with BM25 ranking over sections and path-traversal and symlink protection, which upstream does not have
- `fetch_url`: SSRF guard re-applied on every redirect, response size cap, redirect limit, stdlib `robotparser`, simple HTML cleanup
- `convert_time`: optional `date`, and detection of non-existent and ambiguous wall-clock times around DST changes
- errors surface as MCP tool errors; logging goes to stderr; tests include a protocol-level test with the official MCP client

`sample_notes/` is original to this project. Dependencies (mcp SDK, httpx, markdownify, tzdata) are installed packages and are not vendored.
