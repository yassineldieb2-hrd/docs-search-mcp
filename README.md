# docs-search-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) server in Python that gives an AI client (Claude Desktop,
Claude Code or any MCP client) five tools: search and read a folder of local notes, fetch a public web page as markdown,
and convert times between timezones.

## The problem
Tools exposed to a model are an attack surface. A notes tool must not read outside its folder, and a web-fetch tool must not
let the model (or a prompt injection) make your machine request internal addresses. This server provides useful tools with
those protections built in and tested through a real MCP client.

## Tools
| Tool | What it does |
|---|---|
| `list_notes` | Lists `.md`/`.txt` files under the notes folder |
| `search_notes(query, limit)` | BM25 keyword search over note sections; returns path, heading, score and snippet |
| `read_note(path, max_chars)` | Reads one note; refuses paths outside the folder, symlinks and other file types |
| `fetch_url(url, max_length, start_index, raw)` | Fetches a page as markdown, paginated; honours robots.txt; refuses private addresses |
| `convert_time(source_timezone, time, target_timezone, date?)` | HH:MM conversion between IANA zones, DST-aware for a given date |

All tools are marked read-only through MCP annotations (`fetch_url` additionally `openWorldHint`).

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
Stack: Python 3.10+, the official `mcp` SDK (1.x, FastMCP), httpx, markdownify, zoneinfo/tzdata, pytest + pytest-asyncio.

## Key technical decisions
- **SSRF guard.** The host is resolved, non-public addresses are blocked (private, loopback, link-local), and the check is repeated on every redirect hop. Responses are size-capped and redirects are limited.
- **Path traversal and symlink protection.** The final path is resolved and verified to stay under the notes root.
- **Errors as tool errors.** Invalid input returns `isError: true` with a message the model can act on; the server keeps running. Logs go to stderr so stdout stays the protocol channel.
- **DST-aware time conversion.** An optional `date` makes offsets correct for that day, and non-existent or ambiguous wall-clock times around DST changes are detected.
- **Section-level BM25.** Notes are split by heading so results point at the relevant section, not just the file.
- **FastMCP.** Tool schemas are derived from type hints and docstrings, which keeps schema and implementation in sync.

## How to run
```bash
python -m venv .venv && source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest                                         # 39 tests, no network needed
python examples/client_demo.py                           # starts the server and calls the tools through an MCP client
docs-search-mcp --docs-dir /path/to/your/notes           # run the server (stdio)
```
Configuration: see `.env.example`. To use it from Claude Desktop, add [examples/claude_desktop_config.json](examples/claude_desktop_config.json)
to the MCP config (use the absolute path to `docs-search-mcp` inside your venv if it is not on PATH) and restart the app.

## Example
[examples/client_demo_output.txt](examples/client_demo_output.txt) is real output from `client_demo.py`: searching "stdio logs stdout"
returns the `Transports` section of `mcp-notes.md`, and converting 10:00 Warsaw to Dubai on 2026-07-15 returns 12:00 (UTC+2 to UTC+4).

## Testing
39 tests cover note search and path safety, URL validation and SSRF cases, robots.txt handling, DST edge cases, and a protocol-level
test that starts the server and calls every tool through the official MCP Python client.

## Limitations
- Keyword search only (no embeddings); the index is built at startup, so new notes need a restart
- The SSRF guard resolves DNS before connecting, so a DNS-rebinding attacker could still race it; do not expose the server to untrusted networks
- HTML cleanup is simple and JavaScript-rendered pages return little; there is no authentication on the HTTP transport
- Verified with the official Python MCP client and a local HTTP test server, not inside Claude Desktop

## License
MIT, see [LICENSE](LICENSE). Third-party attributions: [SOURCES.md](SOURCES.md).
