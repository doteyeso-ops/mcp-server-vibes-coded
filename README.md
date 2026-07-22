<!-- mcp-name: io.github.doteyeso-ops/mcp-server-vibes-coded -->

# mcp-server-vibes-coded

MCP server that exposes **Vibes-Coded pay-per-call x402 agent-tool endpoints** as
discoverable MCP tools. Agents find this server on Glama / Smithery / the official
MCP Registry, then call tools that proxy to `https://vibes-coded.com/api/v1/outcomes/{slug}`.

## What it does

- Auto-registers catalog endpoints as MCP tools (fetched live from Vibes-Coded discovery).
- Free-trial endpoints work with no auth. Paid endpoints settle USDC via x402 (HTTP 402 → pay → retry).
- Categories: agent reliability (state / idempotency / drift / retry-storm), memory, cost control,
  supply-chain trust, and utilities (web-search, json-repair, page-markdown).
- Includes a **`pay`** tool that returns the exact 402 challenge (or forwards `PAYMENT-SIGNATURE`).
- Prefer **prepaid** (`X-Vibes-Key`) or a **24h day-pass** (`X-Day-Pass`) over per-call wallet signing.
- **Human fund UI:** https://vibes-coded.com/start ($1 USDC → copy `X-Vibes-Key`).
- **Mid-run rescue (Operator Interrupt):** send header `X-Operator-Notify: https://…` on 402 → poll
  `GET /api/v1/operator-interrupt/{ois_…}` until `status=funded`.

## Install

```bash
pip install mcp-server-vibes-coded
mcp-server-vibes-coded          # stdio MCP for local clients
```

There is **no npm package**. Do not `npx @doteyeso-ops/mcp-server-vibes-coded`.

## Hosted / Docker (Glama, Smithery)

Default (stdio — local clients, MCP Registry OCI, Glama `mcp-proxy`):

```bash
python mcp_server.py
# or: docker run -i --rm ghcr.io/doteyeso-ops/mcp-server-vibes-coded:1.0.3
```

HTTP mode (Smithery / inspectors):

```bash
PORT=3000 MCP_TRANSPORT=streamable-http python mcp_server.py
# health: GET /health  GET /healthz
```

Glama release steps: see [`GLAMA_RELEASE.md`](GLAMA_RELEASE.md) (Glama generates its own image; use stdio CMD, not HTTP).

Env:

- `VIBES_ORIGIN` — API base (default production Railway URL that bypasses Cloudflare)
- `MCP_TRANSPORT=streamable-http` + `PORT` — optional HTTP mode for hosted inspectors
- `HOST` (HTTP mode only)

## Payment

This server is a discovery + proxy wrapper. Payments settle on Vibes-Coded via OpenX402
(Solana USDC). Forward `PAYMENT-SIGNATURE`, or use prepaid / day-pass headers on the backend.

**Preferred (no mid-run wallet):**

1. Operator opens https://vibes-coded.com/start → pays $1 USDC → pastes `X-Vibes-Key` into the agent/MCP env
2. Or machine fund: `POST /api/v1/outcomes/balance/fund`
3. Mid-run without a key: `X-Operator-Notify` → human funds `/start?ois=` → poll for key

- Marketplace: https://vibes-coded.com
- Fund agent: https://vibes-coded.com/start
- Agent docs: https://vibes-coded.com/llms.txt
- Catalog: https://vibes-coded.com/api/v1/outcomes/meta
- Official connector (OpenClaw/Hermes): https://doteyeso-ops.github.io/vibes-coded-agent-connector/
- Glama: https://glama.ai/mcp/servers/@doteyeso-ops/mcp-server-vibes-coded
- Smithery: https://smithery.ai/servers/@doteyeso-ops/mcp-server-vibes-coded
