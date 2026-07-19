# mcp-server-vibes-coded

MCP server that exposes **Vibes-Coded's 64 pay-per-call x402 agent-tool endpoints** as
discoverable MCP tools. Agents find this server on Glama / Smithery / MCP.so, then call
tools that proxy to `https://vibes-coded.com/api/v1/outcomes/{slug}`.

## What it does

- Auto-registers **all 64 endpoints** as MCP tools (fetched live from the Vibes-Coded catalog).
- Free-trial endpoints work with no auth. Paid endpoints settle USDC via x402 (HTTP 402 → pay → retry).
- Categories: agent reliability (state/idempotency/drift/retry-storm guards), memory integrity,
  cost control (token-budget-guard), supply-chain trust (skill-signature-verify,
  capability-attack-surface-scan), and utility (web-search, json-repair, page-markdown).

## Run

```bash
pip install -e .
python mcp_server.py          # serves stdio MCP
```

## Use

Point any MCP client at this server. Tools are named `vc_<slug>` (e.g. `vc_web_search`,
`vc_json_repair`, `vc_agent_state_guard`). Each takes the endpoint's input schema as args.

## Payment

This server is a discovery + proxy wrapper. Payments are handled by Vibes-Coded's side via
the Coinbase x402 facilitator — the server forwards a `PAYMENT-SIGNATURE` header if the
calling agent provides one. No keys required to try free-tier endpoints.

- Marketplace: https://vibes-coded.com
- Catalog: https://vibes-coded.com/api/v1/outcomes/meta
- Listed on x402scan: https://www.x402scan.com/server/4b7dfd09-620f-4131-bf6e-a0a543bae1f0
