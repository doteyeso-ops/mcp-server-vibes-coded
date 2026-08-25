---
name: agent-skill-risk-scan
description: Use before installing an untrusted SKILL.md, MCP plugin, package script, or agent installer. Buys a deterministic supply-chain risk report for $0.05 USDC through FiatDock.
---

# Agent Skill Supply-Chain Risk Scan

Run this gate **before** installing or executing third-party agent skills, MCP plugins, package lifecycle scripts, or copied setup commands.

## What it detects

- downloaded content piped into a shell
- private-key and credential-file references
- secret-bearing environment-variable access
- known external collection endpoints
- operating-system command execution
- destructive filesystem operations
- encoded payload execution
- automatic package lifecycle hooks

The result includes a 0–100 risk score, `allow` / `review` / `block` verdict, triggered rule IDs, evidence locations, SHA-256 content fingerprint, and remediation guidance.

> This is deterministic static analysis. An `allow` result is not proof of provenance or safety.

## Paid call

Service listing: `https://fiatdock.com/s/svc_119fd520-9e87-4b54-b73b-562968163805`

Price: **$0.05 USDC per scan on Base**. FiatDock settles only after the seller returns an answer. A delivery failure is not charged unless the response explicitly contains a `settled` array.

Request a payment quote by posting the complete text as `content`:

```bash
curl -sS -X POST \
  https://fiatdock.com/s/svc_119fd520-9e87-4b54-b73b-562968163805 \
  -H 'Content-Type: application/json' \
  -d '{"content":"PASTE THE COMPLETE SKILL OR PLUGIN TEXT HERE"}'
```

The initial response is HTTP `402` and its `accepts` array lists every payment leg. Nothing is charged by the quote.

After signing each required Base USDC payment authorization, retry the identical request with `PAYMENT-SIGNATURE`. FiatDock x402 v2 expects a base64-encoded JSON **array**, one signed payload per accepted leg:

```bash
curl -sS -X POST \
  https://fiatdock.com/s/svc_119fd520-9e87-4b54-b73b-562968163805 \
  -H 'Content-Type: application/json' \
  -H 'PAYMENT-SIGNATURE: BASE64_JSON_ARRAY_OF_SIGNED_PAYLOADS' \
  -d '{"content":"PASTE THE COMPLETE SKILL OR PLUGIN TEXT HERE"}'
```

## When multiple scanners disagree

Use the separate consensus service to reconcile two to ten reports from tools such as Snyk, Cisco Skill Scanner, Mondoo, or internal scanners:

`https://fiatdock.com/s/svc_392cf062-d72b-4816-9bfb-4eb074d35cc6`

Price: **$0.10 USDC per reconciliation on Base**. Request body:

```json
{
  "reports": [
    {"scanner": "scanner-a", "verdict": "allow", "risk_score": 8, "findings": []},
    {"scanner": "scanner-b", "verdict": "block", "risk_score": 92, "findings": [{"rule_id": "credential-harvest"}]}
  ]
}
```

The result measures agreement, surfaces conflicts, combines rule identifiers, applies a conservative maximum-severity decision, and fingerprints the evidence bundle. Use the same FiatDock 402 → signed `PAYMENT-SIGNATURE` retry flow described above.

## Decision policy

- `block`: do not install or execute; resolve every critical/high finding.
- `review`: require human review and isolate execution.
- `allow`: no known high-risk pattern matched; still verify source, signature, and publisher identity.

Never expose an unrelated secret merely to scan a skill. Scan the skill/plugin text itself.
