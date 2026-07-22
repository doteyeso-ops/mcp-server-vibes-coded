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
2. Push to `main`, then on Glama: **Sync Server** → clear any pinned commit → **Deploy**.

## Admin Dockerfile form

Open: https://glama.ai/mcp/servers/doteyeso-ops/mcp-server-vibes-coded/admin/dockerfile

| Field | Value |
| --- | --- |
| Python version | **3.11** (or 3.12) |
| **Build steps** | `["uv pip install --system -r requirements.txt"]` |
| **CMD arguments** | `["python", "-u", "mcp_server.py"]` |
| Env JSON schema | `{"type":"object","properties":{"VIBES_ORIGIN":{"type":"string","description":"API origin"},"PYTHONUNBUFFERED":{"type":"string"}},"required":[]}` |
| Placeholder parameters | `{"VIBES_ORIGIN":"https://vibes-coded.com"}` |
| Pinned commit SHA | **empty** (after Sync) — do **not** leave `fc0621c…` |

**Form JSON gotchas (Glama validates each field separately):**
- **Placeholder parameters** = flat object of **strings only** (not the env schema). Valid: `{"VIBES_ORIGIN":"https://vibes-coded.com"}` or `{}`.
- **Env JSON schema** = JSON Schema object (different field).
- **Build steps** / **CMD arguments** = JSON **arrays**.
- No smart quotes, no trailing commas, no wrapping in backticks. If the form still says Invalid JSON on placeholders, paste `{}` and set `VIBES_ORIGIN` later.

**Do not** put `mcp-proxy` in CMD arguments — Glama already wraps as `mcp-proxy -- <your CMD>`.

**Do not** set `PORT` or `MCP_TRANSPORT` — Glama needs stdio. Generated CMD becomes `mcp-proxy -- python -u mcp_server.py`.

**Critical:** use `python -u` (unbuffered). Without it, mcp-proxy hangs on “Expected server to respond to ping” ([mcp-proxy#55](https://github.com/punkpeye/mcp-proxy/issues/55)).

### Known failure: `pip: not found` (exit 127)

Glama’s base image installs CPython via **uv** and only symlinks `python` — bare `pip` is **not** on `PATH`.

Wrong:
```json
["pip install -r requirements.txt"]
```

### Known failure: `externally-managed-environment` (PEP 668)

`python -m ensurepip` / `python -m pip` fails on Glama’s uv-managed Python:

```text
error: externally-managed-environment
× This environment is managed by uv and should not be modified.
```

**Right (use this):**
```json
["uv pip install --system -r requirements.txt"]
```

Only if `uv` is missing (it shouldn’t be — Glama installs it in the base layer):
```json
["python -m pip install --break-system-packages --no-cache-dir -r requirements.txt"]
```

### Known failure: still building old SHA `fc0621c`

Log line `git checkout fc0621c…` means the admin form still has a **pinned commit**. Clear the pin, **Sync**, then Deploy — otherwise you rebuild the Jul-20 tree forever.

### Stuck `pending` with empty Docker build logs

That is Glama’s builder queue, not your code — same pattern as “load remote build context then nothing.” Wait a few minutes, or cancel and **Deploy** again after Sync. If it never leaves pending, email **support@glama.ai** with the build id.

### Can we Deploy via the public API / curl?

**No.** `GET https://glama.ai/api/mcp/v1/servers/...` is **read-only directory metadata** (name, tools, env schema). It cannot Sync, Deploy, or Make Release.

There is **no documented public write API** for maintainer Deploy. Official path is admin UI only ([How to Make a Release](https://glama.ai/blog/2026-03-15-how-to-make-a-release)). `glama.json` schema is **only** `$schema` + `maintainers` — cannot embed buildSteps/CMD.

**Escape hatch:** email **support@glama.ai** (or Discord) with the exact build spec below and ask them to apply + run Deploy + score. CC that awesome-mcp #10486 is blocked on quality grade.

## Release

1. **Sync** (latest `main`) + empty pinned SHA
2. **Deploy** with build step above + CMD `python -u mcp_server.py`
3. When green → **Make Release** → version `1.0.3`
4. Score / installability should leave “No Glama release” / quality `?`
5. Confirm public API shows tools: `GET https://glama.ai/api/mcp/v1/servers/doteyeso-ops/mcp-server-vibes-coded` → `tools` non-empty
6. Reply on awesome-mcp-servers#10486 once score badge leaves `?`

## Why verify failed before

1. **`pip: not found`** — bare `pip` on uv-based image (fix with `python -m pip` / `uv pip`).
2. Wrong `glama.json` schema (custom metadata ≠ maintainers).
3. HTTP mode (`PORT` / streamable-http) instead of stdio under `mcp-proxy`.
4. CMD included `mcp-proxy` twice, or omitted `-u`.
5. Pinned to an old commit (`fc0621c`) instead of Sync’d `main`.
