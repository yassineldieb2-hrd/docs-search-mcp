# MCP notes

## Transports
stdio servers are launched by the client as a subprocess and talk JSON-RPC over stdin/stdout, so they must never print logs to stdout. Streamable HTTP servers listen on a port.

## Tool design
Give each tool a clear description and a small typed schema. Mark read-only tools with annotations. Return errors as tool errors, not crashes.
