"""Vibes-Coded MCP server — exposes all 64 pay-per-call x402 endpoints as MCP tools.

Agents discover this server on Glama / Smithery / MCP.so, then call tools that
proxy to https://vibes-coded.com/api/v1/outcomes/{slug}. Free-trial endpoints work
with no auth; paid endpoints require the caller to satisfy x402 (the server forwards
the PAYMENT-SIGNATURE header if the client provides one). This server is purely a
discovery + proxy wrapper — payments settle on Vibes-Coded's side via the CDP
facilitator.

Run:  python mcp_server.py   (serves stdio MCP)
Publish: smithery publish / glama add-server / mcp.so/submit
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from mcp.server.fastmcp import FastMCP

ORIGIN = os.getenv("VIBES_ORIGIN", "https://vibes-coded.com")
META_URL = f"{ORIGIN}/api/v1/outcomes/meta"

mcp = FastMCP("vibes-coded-agent-tools")


def _fetch_catalog() -> list[dict]:
    req = urllib.request.Request(META_URL, headers={"User-Agent": "vibes-coded-mcp/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return data.get("resources", [])


def _call_endpoint(slug: str, payload: dict, payment_sig: str | None = None) -> dict:
    url = f"{ORIGIN}/api/v1/outcomes/{slug}"
    body = json.dumps(payload or {}).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "vibes-coded-mcp/1.0"}
    if payment_sig:
        headers["PAYMENT-SIGNATURE"] = payment_sig
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return json.loads(raw)
        except Exception:
            return {"error": f"HTTP {e.code}", "detail": raw[:500]}


# Build tools dynamically from the live catalog.
CATALOG = _fetch_catalog()
for _res in CATALOG:
    _slug = _res["slug"]
    _title = _res.get("title", _slug)
    _desc = _res.get("description", "")
    _price = _res.get("price_usd", "0")
    _props = (_res.get("input_schema") or {}).get("properties", {})
    _required = (_res.get("input_schema") or {}).get("required", [])
    _doc = f"{_title} (${_price} USDC via x402). {_desc}"

    # Build a per-tool function with typed kwargs from the schema.
    _param_names = list(_props.keys())

    def _make_handler(slug: str, params: list[str]):
        def _handler(**kwargs: Any) -> str:
            payload = {k: v for k, v in kwargs.items() if v is not None}
            result = _call_endpoint(slug, payload)
            return json.dumps(result, indent=2, default=str)
        return _handler

    _fn = _make_handler(_slug, _param_names)
    _fn.__name__ = f"vc_{_slug.replace('-', '_')}"
    _fn.__doc__ = _doc

    # Register with FastMCP; describe params from schema.
    mcp.add_tool(
        _fn,
        name=f"vc_{_slug.replace('-', '_')}",
        description=_doc,
    )


if __name__ == "__main__":
    mcp.run()
