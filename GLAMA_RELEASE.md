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
| **CMD arguments** | `["python", "-u", "mcp_server.py"]` |
| Env JSON schema | `{"type":"object","properties":{"VIBES_ORIGIN":{"type":"string","description":"API origin"},"PYTHONUNBUFFERED":{"type":"string"}},"required":[]}` |
| Placeholder parameters | `{"PYTHONUNBUFFERED":"1"}` (optional; `-u` already covers it) |
| Pinned commit SHA | **empty** (after Sync) |

Do **not** set `PORT` or `MCP_TRANSPORT` — Glama needs stdio. Generated CMD becomes `mcp-proxy -- python -u mcp_server.py`.

**Critical:** use `python -u` (unbuffered). Without it, mcp-proxy hangs on “Expected server to respond to ping” ([mcp-proxy#55](https://github.com/punkpeye/mcp-proxy/issues/55)).

### Stuck `pending` with empty Docker build logs

That is Glama’s builder queue, not your code — same pattern as “load remote build context then nothing.” Wait a few minutes, or cancel and **Deploy** again after Sync. If it never leaves pending, email **support@glama.ai** with the build id.

## Release

1. **Deploy** (build test)
2. When green → **Make Release** → version `1.0.3`
3. Score / installability should leave “No Glama release” / quality `?`
4. Confirm public API shows tools: `GET https://glama.ai/api/mcp/v1/servers/doteyeso-ops/mcp-server-vibes-coded` → `tools` non-empty
5. Reply on awesome-mcp-servers#10486 once score badge leaves `?`

## Why verify failed before

Wrong `glama.json` schema (custom metadata ≠ maintainers), and/or HTTP mode (`PORT` / streamable-http) instead of stdio under `mcp-proxy`.
