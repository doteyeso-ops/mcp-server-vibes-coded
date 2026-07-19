"""Vibes-Coded MCP server — exposes ALL pay-per-call x402 endpoints (91) as MCP tools.

Source of truth: the live /.well-known/x402.json discovery doc (71 outcome endpoints
+ 20 product aliases = 91 callable x402 resources). Agents discover this server on
Glama / Smithery / MCP.so, then call tools that proxy to the resource's real path.
Free-trial endpoints work with no auth; paid endpoints require the caller to satisfy
x402 (the server forwards the PAYMENT-SIGNATURE header if the client provides one).
This server is purely a discovery + proxy wrapper — payments settle on Vibes-Coded's
side via the CDP facilitator.

Run:  python mcp_server.py   (serves stdio MCP)
Publish: smithery publish / glama add-server / mcp.so/submit
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP

ORIGIN = os.getenv("VIBES_ORIGIN", "https://vibes-coded-production.up.railway.app")
WELLKNOWN_URL = f"{ORIGIN}/.well-known/x402.json"

mcp = FastMCP("vibes-coded-agent-tools")


def _fetch_resources() -> list[dict]:
    """Fetch all x402 resources from the live discovery doc."""
    req = urllib.request.Request(WELLKNOWN_URL, headers={"User-Agent": "vibes-coded-mcp/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return data.get("resources", [])


def _endpoint_path(res: dict) -> str:
    """Return the call path (strip origin). Supports full URL or relative path."""
    p = res.get("path") or res.get("href") or res.get("url") or ""
    if p.startswith("http"):
        p = urlparse(p).path
    return p


def _call_resource(path: str, payload: dict, payment_sig: str | None = None) -> dict:
    url = f"{ORIGIN}{path}"
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


# Build tools dynamically from the live discovery doc (all 91 x402 resources).
RESOURCES = _fetch_resources()
_seen = set()
for _res in RESOURCES:
    _path = _endpoint_path(_res)
    if not _path:
        continue
    # dedupe by path
    if _path in _seen:
        continue
    _seen.add(_path)

    _slug = _res.get("slug") or _path.strip("/").replace("/", "_")
    _title = _res.get("title") or _res.get("name") or _slug
    _desc = _res.get("description", "")
    _price = _res.get("price_usd", _res.get("price_cents", "0"))
    _price_str = f"${float(_price)/100:.2f}" if isinstance(_price, (int, float)) else str(_price)
    _props = (_res.get("input_schema") or {}).get("properties", {})
    _doc = f"{_title} ({_price_str} USDC via x402). {_desc}  [calls {_path}]"

    _param_names = list(_props.keys())

    def _make_handler(path: str, params: list[str]):
        def _handler(**kwargs: Any) -> str:
            payload = {k: v for k, v in kwargs.items() if v is not None}
            result = _call_resource(path, payload)
            return json.dumps(result, indent=2, default=str)
        return _handler

    _fn = _make_handler(_path, _param_names)
    _fn.__name__ = f"vc_{_slug.replace('-', '_').replace('/', '_')}"
    _fn.__doc__ = _doc

    mcp.add_tool(
        _fn,
        name=f"vc_{_slug.replace('-', '_').replace('/', '_')}",
        description=_doc,
    )


if __name__ == "__main__":
    # Default to stdio for local MCP clients. When PORT is set (e.g. Railway) or
    # MCP_TRANSPORT=streamable-http, serve over HTTP so Smithery / remote agents
    # can connect to a hosted endpoint.
    _transport = os.getenv("MCP_TRANSPORT")
    _port = os.getenv("PORT")
    if _transport == "streamable-http" or _port:
        mcp.settings.host = os.getenv("HOST", "0.0.0.0")
        mcp.settings.port = int(_port or os.getenv("MCP_PORT", "8000"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
