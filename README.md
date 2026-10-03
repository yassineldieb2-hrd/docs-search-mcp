# docs-search-mcp

A small [Model Context Protocol](https://modelcontextprotocol.io) server in Python that gives an AI client (Claude Desktop,
Claude Code, or any MCP client) five tools: search and read a folder of local notes, fetch a public web page as markdown,
and convert times between timezones.

Based in part on the `fetch` and `time` reference servers from [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers). See [SOURCES.md](SOURCES.md).

## Why I built it
To learn how MCP works end to end: tool schemas, annotations, transports, error handling, and testing a server through
a real MCP client - and to practise the security thinking tools need (path traversal, SSRF).

## Tools
| Tool | What it does |
|---|---|
| `list_notes` | Lists `.md`/`.txt` files under the notes folder |
| `search_notes(query, limit)` | BM25 keyword search over note sections; returns path, heading, score, snippet |
| `read_note(path, max_chars)` | Reads one note; refuses paths outside the folder, symlinks, other file types |
| `fetch_url(url, max_length, start_index, raw)` | Fetches a page → markdown, paginated; honours robots.txt; refuses private addresses |
| `convert_time(source_timezone, time, target_timezone, date?)` | HH:MM conversion between IANA zones, DST-aware for a given date |

All tools are marked read-only via MCP annotations (`fetch_url` additionally `openWorldHint`).

## Architecture
```
MCP client (Claude Desktop / Code / your script)
        | JSON-RPC over stdio (or streamable HTTP)
        v
  server.py  (FastMCP: tool registration, schemas from type hints, annotations, error mapping)
     |-- notes.py     BM25 index over sections, safe path resolution
     |-- web.py       SSRF guard -> robots.txt -> size-capped fetch -> HTML to markdown
     '-- timeconv.py  zoneinfo conversion, DST edge cases
```

## Tech stack
Python 3.10+, official `mcp` SDK (1.x, FastMCP), httpx, markdownify, zoneinfo/tzdata, pytest + pytest-asyncio.

## How to run
```bash
python -m venv .venv && source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest                                         # 39 tests, no network needed
python examples/client_demo.py                           # starts the server and calls tools
docs-search-mcp --docs-dir /path/to/your/notes           # run it yourself (stdio)
```
Use with Claude Desktop: add [examples/claude_desktop_config.json](examples/claude_desktop_config.json) to your MCP config
(use the absolute path to `docs-search-mcp` inside your venv if it is not on PATH), then restart the app.

## Example
[examples/client_demo_output.txt](examples/client_demo_output.txt) is real output from running `client_demo.py`, e.g. searching
"stdio logs stdout" returns the `Transports` section of `mcp-notes.md`, and converting 10:00 Warsaw → Dubai on 2026-07-15 returns 12:00 (UTC+2 → UTC+4).

## What I changed / added vs. upstream
See [SOURCES.md](SOURCES.md): a new local-notes toolset, SSRF-guarded fetch, DST-aware time conversion, FastMCP-based server, tests.

## Key Technical Concepts
- **MCP**: a protocol where a *client* (inside an AI app) discovers a server's *tools* (also resources, prompts) and the model decides when to call them. Messages are JSON-RPC 2.0.
- **Transports**: stdio (client launches the server; stdout is the protocol channel, so logs go to stderr) vs. streamable HTTP (server on a port).
- **Tool schema**: name + description + JSON Schema for inputs. FastMCP derives it from Python type hints and the docstring; the description is what the model reads to decide when to use a tool.
- **Tool annotations**: hints like `readOnlyHint` and `openWorldHint` that let clients decide about confirmations. They are hints, not enforcement.
- **Tool errors vs. protocol errors**: bad input returns `isError: true` with a message the model can react to; the server keeps running.
- **Path traversal**: resolve the final path (following symlinks) and verify it stays under the root.
- **SSRF**: a fetch tool lets the model (or a prompt injection) make your machine request URLs. Resolve the host, block non-public IPs, re-check on every redirect.
- **BM25**: ranking by term frequency × inverse document frequency with length normalisation.
- **DST edge cases**: some local times don't exist (spring forward) and some occur twice (fall back).

## Limitations
- Keyword search only (no embeddings); the index is built at startup, so new notes need a restart.
- SSRF guard resolves DNS before connecting; a DNS-rebinding attacker could still race it. Don't expose this server to untrusted networks.
- HTML cleanup is simple; JavaScript-rendered pages return little. No authentication on the HTTP transport.
- Tested with the official Python MCP client and a local HTTP test server; I have not tested it inside Claude Desktop.

## Future improvements
Hybrid (embedding + BM25) search reusing ideas from my `rag-eval-lab`, MCP resources for notes, file watching/reindex, auth for HTTP transport, readability-style article extraction.
