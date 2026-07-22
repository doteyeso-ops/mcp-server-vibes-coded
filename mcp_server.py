"""Vibes-Coded MCP server — exposes pay-per-call x402 endpoints as MCP tools.

Source of truth: live /.well-known/x402.json. Agents discover this server on
Glama / Smithery / MCP Registry, then call tools that proxy to Vibes-Coded.

Run (stdio):  python mcp_server.py
Hosted HTTP:  MCP_TRANSPORT=streamable-http PORT=3000 python mcp_server.py
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("vibes-coded-mcp")
# stderr only — stdout is the MCP JSON-RPC channel (mcp-proxy / Glama).
logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
# Unbuffered stdio even if launcher forgets `python -u`.
os.environ.setdefault("PYTHONUNBUFFERED", "1")


from mcp.server.fastmcp import FastMCP

ORIGIN = os.getenv("VIBES_ORIGIN", "https://vibes-coded-production.up.railway.app").rstrip("/")
PUBLIC_ORIGIN = "https://vibes-coded.com"
WELLKNOWN_URL = f"{ORIGIN}/.well-known/x402.json"
VERSION = "1.0.3"

mcp = FastMCP("vibes-coded-agent-tools")

# Minimal tools always registered so Glama/Smithery inspectors never see an empty
# tool list when the catalog fetch is blocked/slow at cold start.
_FALLBACK_SLUGS = (
    "agent-state-guard",
    "idempotency-guard",
    "drift-guard",
    "retry-storm-guard",
    "json-repair",
    "web-search",
    "page-markdown",
)


def _fetch_resources(timeout: float = 3.0) -> list[dict]:
    """Fetch x402 resources. Short timeout so Glama mcp-proxy verify never stalls."""
    req = urllib.request.Request(
        WELLKNOWN_URL,
        headers={"User-Agent": f"vibes-coded-mcp/{VERSION}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data.get("resources", []) or []


def _endpoint_path(res: dict) -> str:
    """Return the call path (strip origin). Supports full URL or relative path."""
    p = res.get("path") or res.get("href") or res.get("url") or ""
    if p.startswith("http"):
        p = urlparse(p).path
    return p


def _call_resource(path: str, payload: dict, payment_sig: str | None = None) -> dict:
    url = path if path.startswith("http") else f"{ORIGIN}{path}"
    body = json.dumps(payload or {}).encode()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": f"vibes-coded-mcp/{VERSION}",
    }
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


def _register_slug_tool(slug: str, path: str, title: str, desc: str, price_str: str) -> None:
    name = f"vc_{slug.replace('-', '_').replace('/', '_')}"
    if any(t.name == name for t in mcp._tool_manager.list_tools()):
        return
    doc = f"{title} ({price_str} USDC via x402). {desc}  [calls {path}]"

    def _make_handler(p: str):
        def _handler(**kwargs: Any) -> str:
            payload = {k: v for k, v in kwargs.items() if v is not None}
            result = _call_resource(p, payload)
            return json.dumps(result, indent=2, default=str)

        return _handler

    fn = _make_handler(path)
    fn.__name__ = name
    fn.__doc__ = doc
    mcp.add_tool(fn, name=name, description=doc)


# Guarantee a non-empty tool surface for inspectors first (Glama verify is fast).
for _slug in _FALLBACK_SLUGS:
    _register_slug_tool(
        _slug,
        f"/api/v1/outcomes/{_slug}",
        _slug,
        "Vibes-Coded outcome API (fallback registration).",
        "varies",
    )

# Enrich from live discovery; never block verify more than a few seconds.
try:
    RESOURCES = _fetch_resources(timeout=3.0)
    logger.info("catalog loaded: %s resources", len(RESOURCES))
except Exception as _e:
    logger.warning("catalog fetch failed at startup: %s", _e)
    RESOURCES = []

_seen_paths: set[str] = set()
for _res in RESOURCES:
    _path = _endpoint_path(_res)
    if not _path or _path in _seen_paths:
        continue
    _seen_paths.add(_path)
    _slug = _res.get("slug") or _res.get("x-canonical-slug") or _path.strip("/").replace("/", "_")
    _title = _res.get("title") or _res.get("name") or _slug
    _desc = _res.get("description") or ""
    _price = _res.get("price_usd", _res.get("price_cents", "0"))
    if isinstance(_price, (int, float)) and _price > 5:
        _price_str = f"${float(_price) / 100:.2f}"
    else:
        _price_str = f"${_price}" if not str(_price).startswith("$") else str(_price)
    _register_slug_tool(str(_slug), _path, str(_title), str(_desc), _price_str)


def _slug_to_path(slug: str) -> str | None:
    for _r in RESOURCES:
        _doc_slug = _r.get("x-canonical-slug") or _r.get("slug") or ""
        if _doc_slug == slug:
            return _r.get("url") or _endpoint_path(_r)
    return f"{ORIGIN}/api/v1/outcomes/{slug}"


@mcp.tool()
def pay(slug: str, payment_signature: str | None = None, **kwargs: Any) -> str:
    """Pay for and call a Vibes-Coded x402 endpoint.

    Args:
        slug: endpoint slug, e.g. "web-search" or "agent-state-guard".
        payment_signature: optional x402 PAYMENT-SIGNATURE from your wallet.
        **kwargs: endpoint input fields.

    Prefer prepaid X-Vibes-Key or a 24h day-pass over per-call signing when possible.
    """
    path = _slug_to_path(slug)
    if not path:
        return json.dumps({"error": f"Unknown slug '{slug}'."}, indent=2)
    if payment_signature:
        result = _call_resource(path, kwargs, payment_sig=payment_signature)
        return json.dumps(result, indent=2, default=str)
    result = _call_resource(path, kwargs)
    if isinstance(result, dict) and result.get("x402Version") is not None:
        accepts = (result.get("accepts") or [{}])[0] if result.get("accepts") else {}
        req = accepts.get("requiredPayment") or accepts
        pay_to = req.get("payTo") or accepts.get("payTo")
        amount = req.get("amount") or req.get("maxAmountRequired")
        asset = req.get("asset")
        network = req.get("network")
        out = {
            "payment_required": True,
            "x402Version": result.get("x402Version"),
            "pay_to": pay_to,
            "amount": amount,
            "asset": asset,
            "network": network,
            "preferred": {
                "human_fund": f"{PUBLIC_ORIGIN}/start",
                "prepaid_fund": f"{ORIGIN}/api/v1/outcomes/balance/fund",
                "day_pass": f"{ORIGIN}/api/v1/outcomes/day-pass",
                "header_prepaid": "X-Vibes-Key",
                "header_day_pass": "X-Day-Pass",
                "operator_interrupt": {
                    "header": "X-Operator-Notify",
                    "how": "On 402, send HTTPS webhook URL; poll GET /api/v1/operator-interrupt/{ois_…} for key",
                    "poll": f"{PUBLIC_ORIGIN}/api/v1/operator-interrupt/{{session_id}}",
                },
            },
            "example_calls": result.get("example_calls"),
            "raw_challenge": result,
            "note": (
                "No npm package — use pip/Docker/registry. Prefer https://vibes-coded.com/start "
                "($1 prepaid) or X-Operator-Notify mid-run; else PAYMENT-SIGNATURE / day-pass."
            ),
        }
        return json.dumps(out, indent=2, default=str)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def health() -> str:
    """Liveness check for hosted inspectors (Glama / Smithery)."""
    return json.dumps(
        {
            "ok": True,
            "service": "mcp-server-vibes-coded",
            "version": VERSION,
            "origin": ORIGIN,
            "tools": len(mcp._tool_manager.list_tools()),
            "catalog_resources": len(RESOURCES),
        },
        indent=2,
    )


def _attach_http_routes(app) -> None:
    """Health + MCP server card for Glama/Smithery Docker verification."""
    from starlette.responses import JSONResponse, PlainTextResponse
    from starlette.routing import Route

    def _health(_request):
        return JSONResponse(
            {
                "ok": True,
                "service": "mcp-server-vibes-coded",
                "version": VERSION,
                "tools": len(mcp._tool_manager.list_tools()),
            }
        )

    def _ready(_request):
        return PlainTextResponse("ok\n", status_code=200)

    def _server_card(_request):
        tools = []
        for _t in mcp._tool_manager.list_tools():
            tools.append(
                {
                    "name": _t.name,
                    "description": _t.description or "",
                    "inputSchema": getattr(_t, "parameters", None)
                    or {"type": "object", "properties": {}},
                }
            )
        return JSONResponse(
            {
                "serverInfo": {"name": "vibes-coded-agent-tools", "version": VERSION},
                "tools": tools,
                "resources": [],
                "prompts": [],
            }
        )

    for path, handler in (
        ("/health", _health),
        ("/healthz", _ready),
        ("/", _ready),
        ("/.well-known/mcp/server-card.json", _server_card),
    ):
        app.router.routes.insert(0, Route(path, handler, methods=["GET"]))


def main() -> None:
    """CLI entrypoint used by pyproject [project.scripts] and Docker."""
    transport = os.getenv("MCP_TRANSPORT")
    port = os.getenv("PORT")
    if transport == "streamable-http" or port:
        mcp.settings.host = os.getenv("HOST", "0.0.0.0")
        mcp.settings.port = int(port or os.getenv("MCP_PORT", "3000"))
        app = mcp.streamable_http_app()
        _attach_http_routes(app)
        import uvicorn

        logger.info(
            "starting streamable-http on %s:%s (%s tools)",
            mcp.settings.host,
            mcp.settings.port,
            len(mcp._tool_manager.list_tools()),
        )
        uvicorn.run(app, host=mcp.settings.host, port=mcp.settings.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
