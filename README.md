# mcp-server-vibes-coded

MCP server that exposes **Vibes-Coded's 93 pay-per-call x402 agent-tool endpoints** as
discoverable MCP tools. Agents find this server on Glama / Smithery / MCP.so, then call
tools that proxy to `https://vibes-coded.com/api/v1/outcomes/{slug}`.

## What it does

- Auto-registers **all 93 endpoints** as MCP tools (fetched live from the Vibes-Coded catalog).
- Free-trial endpoints work with no auth. Paid endpoints settle USDC via x402 (HTTP 402 → pay → retry).
- Categories: agent reliability (state / idempotency / drift / retry-storm / 402-failure guards),
  memory integrity, cost control (token-budget-guard), supply-chain trust
  (skill-signature-verify, capability-attack-surface-scan), and utilities (web-search, json-repair, page-markdown).
- Includes a **`pay` tool** that closes the x402 loop: call any endpoint, and if it requires
  payment it returns the exact challenge (payTo / amount / asset / network) so your wallet can settle.

## Run

```bash
pip install -e .
python mcp_server.py          # serves stdio MCP
```

For a hosted endpoint (Smithery / Glama), the server also serves over HTTP when `PORT` is set:

```bash
PORT=8080 python mcp_server.py
```

## Use

Point any MCP client at this server. Tools are named `vc_<slug>` (e.g. `vc_web_search`,
`vc_json_repair`, `vc_agent_state_guard`). Each takes the endpoint's input schema as args.

### Day-pass (recommended for agents)

Instead of signing a separate x402 transaction per paid call, buy a **24h day-pass**
(one payment, ~$0.50) and call any guard freely:

```bash
# 1) buy the pass (returns a token)
npx -y @doteyeso-ops/mcp-server-vibes-coded   # then call pay(slug="day-pass")
# 2) send the token on every guard call
X-Day-Pass: <token>
```

## Payment

This server is a discovery + proxy wrapper. Payments are handled by Vibes-Coded's backend via
the Coinbase x402 facilitator — the server forwards a `PAYMENT-SIGNATURE` header if the
calling agent provides one. No keys required to try free-tier endpoints.

- Marketplace: https://vibes-coded.com
- Catalog: https://vibes-coded.com/api/v1/outcomes/meta
- Listed on x402scan: https://www.x402scan.com/server/4b7dfd09-620f-4131-bf6e-a0a543bae1f0
