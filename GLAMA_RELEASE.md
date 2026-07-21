# Glama release (admin UI)

Glama does **not** use this repo's `Dockerfile`. It generates one and wraps CMD with `mcp-proxy` for **stdio** MCP (`initialize` + `tools/list`).

## Repo prerequisites

1. `glama.json` must be exactly:
   ```json
   {
     "$schema": "https://glama.ai/mcp/schemas/server.json",
     "maintainers": ["doteyeso-ops"]
   }
   ```
2. Push to `main`, then on Glama: **Sync Server** → **Claim** (Score tab) if needed.

## Admin Dockerfile form

Open: https://glama.ai/mcp/servers/doteyeso-ops/mcp-server-vibes-coded/admin/dockerfile

| Field | Value |
| --- | --- |
| Python version | **3.11** (or 3.12) |
| **Build steps** | `["pip install --no-cache-dir -r requirements.txt"]` |
| **CMD arguments** | `["python", "mcp_server.py"]` |
| Env JSON schema | `{"type":"object","properties":{"VIBES_ORIGIN":{"type":"string","description":"API origin"}},"required":[]}` |
| Placeholder parameters | `{}` |
| Pinned commit SHA | **empty** (after Sync) |

Do **not** set `PORT` or `MCP_TRANSPORT` — Glama needs stdio. Generated CMD becomes `mcp-proxy -- python mcp_server.py`.

## Release

1. **Deploy** (build test)
2. When green → **Make Release** → version `1.0.2`
3. Score / installability should leave “No Glama release”

## Why verify failed before

Wrong `glama.json` schema (custom metadata ≠ maintainers), and/or HTTP mode (`PORT` / streamable-http) instead of stdio under `mcp-proxy`.
