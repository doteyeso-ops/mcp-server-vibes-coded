---
name: page-human-x402
description: When a Vibes-Coded or x402 tool returns HTTP 402, show print_to_user to the human in chat and send them to /start. Use in Cursor, Claude Code, and OpenClaw when the operator is sitting with the agent.
---

# Page the human (x402)

You cannot sign a wallet. The human next to you can.

## When this applies

A tool or HTTP call returned `402`, `payment_required`, `x402Version`, or a JSON field `print_to_user`.

## Do this

1. Stop retrying signatures.
2. Show `print_to_user` **verbatim** if present.
3. If missing, say exactly:

```
Please open https://vibes-coded.com/start and pay $1 USDC, then paste the vb_ key back here (header X-Vibes-Key). I cannot sign a wallet.
```

4. After they paste a `vb_…` key, retry the original call with `X-Vibes-Key`.
5. Optional: claim a smoke trial first (no wallet):

```bash
curl -sS -A "YourAgent/1.0 (+https://example.com)" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"stable-id-for-your-agent"}' \
  https://vibes-coded.com/api/v1/outcomes/balance/trial/claim
```

## Cursor MCP

```json
{
  "mcpServers": {
    "vibes-coded": {
      "url": "https://vibes-coded-mcp-production.up.railway.app/mcp"
    }
  }
}
```

Deeplink: see `https://vibes-coded.com/.well-known/mcp.json` → `cursor.deeplink`.
