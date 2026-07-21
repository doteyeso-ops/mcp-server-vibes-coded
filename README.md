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
# or: docker run -i --rm ghcr.io/doteyeso-ops/mcp-server-vibes-coded:1.0.2
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

- Marketplace: https://vibes-coded.com
- Agent docs: https://vibes-coded.com/llms.txt
- Catalog: https://vibes-coded.com/api/v1/outcomes/meta
- Glama: https://glama.ai/mcp/servers/@doteyeso-ops/mcp-server-vibes-coded
- Smithery: https://smithery.ai/servers/@doteyeso-ops/mcp-server-vibes-coded
