import json
from pathlib import Path

data = {
    "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
    "name": "io.github.doteyeso-ops/mcp-server-vibes-coded",
    "description": (
        "MCP server exposing Vibes-Coded pay-per-call x402 agent-tool endpoints "
        "(reliability guards, memory, cost control) with a pay tool and day-pass."
    ),
    "repository": {
        "url": "https://github.com/doteyeso-ops/mcp-server-vibes-coded",
        "source": "github",
    },
    "version": "1.0.1",
    "packages": [
        {
            "registryType": "pypi",
            "identifier": "mcp-server-vibes-coded",
            "version": "1.0.1",
            "transport": {"type": "stdio"},
        }
    ],
}
Path("server.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print("ok", Path("server.json").stat().st_size)
