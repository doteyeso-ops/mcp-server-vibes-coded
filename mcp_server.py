"""Vibes-Coded MCP server — exposes ALL pay-per-call x402 endpoints (123) as MCP tools.

Source of truth: the live /.well-known/x402.json discovery doc (93 outcome endpoints
+ 30 product aliases = 123 callable x402 resources). Agents discover this server on
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
import logging
import os
import urllib.request
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("vibes-coded-mcp")

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
    url = path if path.startswith("http") else f"{ORIGIN}{path}"
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


# Build tools dynamically from the live discovery doc (all 91+ x402 resources).
# Resilient: if the catalog fetch fails (e.g. sandboxed inspector with no
# outbound network), start anyway with whatever registered — never crash at import.
try:
    RESOURCES = _fetch_resources()
except Exception as _e:
    logger.warning("catalog fetch failed at startup: %s", _e)
    RESOURCES = []
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


# --- pay tool: closes the x402 loop for agents that hit a 402 ---
# The backend's 402 response advertises `npx @doteyeso-ops/mcp-server-vibes-coded pay <slug>`.
# This tool makes that command REAL: it calls the endpoint, and if a payment is required,
# returns the exact challenge (payTo / amount / asset / network) plus a copy-paste command.
# If the agent already settled with its own wallet, pass payment_signature to forward it.
# Deployed 2026-07-20: previously the `pay` subcommand was a dead CTA on every 402.
# Defined BEFORE the `if __name__` block so it registers before mcp.run()/streamable_http_app().
def _slug_to_path(slug: str) -> str | None:
    """Resolve a slug to its call URL using the live discovery doc.

    The doc keys endpoints by `x-canonical-slug` (fallback `slug`) and carries the
    real endpoint in `url`. Return the full URL so we call the exact path.
    """
    for _r in RESOURCES:
        _doc_slug = _r.get("x-canonical-slug") or _r.get("slug") or ""
        if _doc_slug == slug:
            return _r.get("url") or _endpoint_path(_r)
    # fallback: canonical outcome path (all outcome endpoints live here)
    return f"{ORIGIN}/api/v1/outcomes/{slug}"


@mcp.tool()
def pay(slug: str, payment_signature: str | None = None, **kwargs: Any) -> str:
    """Pay for and call a Vibes-Coded x402 endpoint.

    Args:
        slug: the endpoint slug, e.g. "web-search" or "crypto-price-batch".
        payment_signature: optional x402 PAYMENT-SIGNATURE from your own wallet.
            If provided, it is forwarded and the result is returned directly.
        **kwargs: the endpoint's input fields (e.g. query=..., symbols=[...]).

    If no payment_signature is given and the endpoint requires payment, this returns
    the exact 402 challenge (payTo, amount, asset, network) and a one-line command
    so your x402 client / wallet can settle, then re-call with the signature.
    """
    path = _slug_to_path(slug)
    if not path:
        try:
            for _r in _fetch_resources():
                if (_r.get("slug") or "") == slug:
                    path = _endpoint_path(_r)
                    break
        except Exception:
            pass
    if not path:
        return json.dumps({"error": f"Unknown slug '{slug}'. List tools with vc_* prefix."}, indent=2)
    if payment_signature:
        result = _call_resource(path, kwargs, payment_sig=payment_signature)
        return json.dumps(result, indent=2, default=str)
    # no signature -> call, capture 402 challenge
    result = _call_resource(path, kwargs)
    if isinstance(result, dict) and result.get("x402Version") is not None:
        accepts = (result.get("accepts") or [{}])[0] if result.get("accepts") else {}
        req = accepts.get("requiredPayment") or accepts  # x402 v2 nests under requiredPayment
        pay_to = req.get("payTo") or accepts.get("payTo")
        amount = req.get("amount") or req.get("maxAmountRequired")
        asset = req.get("asset")
        network = req.get("network")
        cmd = (
            f"# Settle with your x402 wallet, then re-call with the PAYMENT-SIGNATURE:\n"
            f"# payTo={pay_to} amount={amount} asset={asset} network={network}\n"
            f"npx -y @doteyeso-ops/mcp-server-vibes-coded   # then call pay(slug='{slug}', "
            f"payment_signature=<your-proof>, **inputs)"
        )
        out = {
            "payment_required": True,
            "x402Version": result.get("x402Version"),
            "pay_to": pay_to,
            "amount": amount,
            "asset": asset,
            "network": network,
            "pay_command": cmd,
            "raw_challenge": result,
        }
        return json.dumps(out, indent=2, default=str)
    return json.dumps(result, indent=2, default=str)


if __name__ == "__main__":
    # Default to stdio for local MCP clients. When PORT is set (e.g. Railway) or
    # MCP_TRANSPORT=streamable-http, serve over HTTP so Smithery / remote agents
    # can connect to a hosted endpoint.
    _transport = os.getenv("MCP_TRANSPORT")
    _port = os.getenv("PORT")
    if _transport == "streamable-http" or _port:
        mcp.settings.host = os.getenv("HOST", "0.0.0.0")
        mcp.settings.port = int(_port or os.getenv("MCP_PORT", "8000"))

        # Build the streamable-HTTP Starlette app and attach a static Smithery
        # server card at /.well-known/mcp/server-card.json so the registry can
        # index us without a live scan (per Smithery publish docs, Option 3).
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        def _server_card(_request):
            tools = []
            for _t in mcp._tool_manager.list_tools():
                tools.append({
                    "name": _t.name,
                    "description": _t.description or "",
                    "inputSchema": getattr(_t, "parameters", None) or {"type": "object", "properties": {}},
                })
            return JSONResponse({
                "serverInfo": {"name": "vibes-coded-agent-tools", "version": "1.0.1"},
                "tools": tools,
                "resources": [],
                "prompts": [],
            })

        _app = mcp.streamable_http_app()
        _app.router.routes.append(
            Route("/.well-known/mcp/server-card.json", _server_card, methods=["GET"])
        )

        import uvicorn

        uvicorn.run(_app, host=mcp.settings.host, port=mcp.settings.port)
    else:
        mcp.run()

