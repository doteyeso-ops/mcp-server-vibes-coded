from __future__ import annotations

import json
import math
import re
from typing import Any

from pydantic import Field
from mcp.types import ToolAnnotations


READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)


def _tokens(value: str | None) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(str(value or ""))]


def _slug(resource: dict[str, Any]) -> str:
    return str(
        resource.get("id")
        or resource.get("x-canonical-slug")
        or resource.get("slug")
        or ""
    ).strip()


def _title(resource: dict[str, Any]) -> str:
    return str(resource.get("title") or resource.get("name") or _slug(resource)).strip()


def _description(resource: dict[str, Any]) -> str:
    return str(resource.get("description") or resource.get("summary") or "").strip()


def _category(resource: dict[str, Any]) -> str:
    raw = resource.get("category") or resource.get("type") or resource.get("group") or ""
    if isinstance(raw, list):
        return ", ".join(str(x) for x in raw if x)
    return str(raw).strip()


def _price_usd(resource: dict[str, Any]) -> float | None:
    price = resource.get("price")
    if isinstance(price, dict):
        for key in ("amount", "usd", "price_usd", "value"):
            if key in price:
                price = price[key]
                break

    if price in (None, ""):
        price = resource.get("price_usd")

    if price in (None, ""):
        return None

    if isinstance(price, (int, float)):
        return float(price)

    text = str(price).strip().lower()
    if text in {"free", "$0", "$0.00", "0", "0.0", "0.00"}:
        return 0.0

    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _is_free(resource: dict[str, Any]) -> bool:
    price = _price_usd(resource)
    if price == 0:
        return True
    flags = (
        resource.get("free"),
        resource.get("is_free"),
        resource.get("trial"),
        resource.get("free_tier"),
    )
    return any(v is True for v in flags)


def _resource_url(resource: dict[str, Any], public_origin: str) -> str:
    for key in ("human_url", "listing_url", "homepage", "docs_url"):
        value = resource.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value

    slug = _slug(resource)
    if slug:
        return f"{public_origin.rstrip('/')}/outcomes/{slug}"

    value = resource.get("url") or resource.get("href") or resource.get("path")
    if isinstance(value, str) and value.startswith("http"):
        return value
    return public_origin.rstrip("/")


def _search_text(resource: dict[str, Any]) -> str:
    fields = [
        _slug(resource),
        _title(resource),
        _description(resource),
        _category(resource),
        resource.get("tags"),
        resource.get("keywords"),
        resource.get("capabilities"),
        resource.get("input_schema"),
        resource.get("examples"),
    ]
    return " ".join(
        json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v or "")
        for v in fields
    ).lower()


def _score(resource: dict[str, Any], query: str) -> float:
    q_tokens = _tokens(query)
    if not q_tokens:
        return 1.0

    slug = _slug(resource).lower()
    title = _title(resource).lower()
    description = _description(resource).lower()
    category = _category(resource).lower()
    haystack = _search_text(resource)

    score = 0.0
    phrase = " ".join(q_tokens)

    if phrase and phrase in title:
        score += 20
    if phrase and phrase in slug.replace("-", " "):
        score += 18
    if phrase and phrase in description:
        score += 10

    for token in q_tokens:
        if token in title:
            score += 8
        if token in slug:
            score += 7
        if token in category:
            score += 4
        if token in description:
            score += 3
        elif token in haystack:
            score += 1

    # Favor concise resources with multiple query-term hits without making price
    # affect semantic relevance.
    unique_hits = sum(1 for token in set(q_tokens) if token in haystack)
    score += min(unique_hits, 5) * 1.5
    return score


def summarize_resource(resource: dict[str, Any], public_origin: str) -> dict[str, Any]:
    price = _price_usd(resource)
    slug = _slug(resource)
    return {
        "slug": slug,
        "title": _title(resource),
        "description": _description(resource),
        "category": _category(resource) or None,
        "price_usd": price,
        "free": _is_free(resource),
        "url": _resource_url(resource, public_origin),
        "execution_tool": "pay",
        "execution_args": {"slug": slug} if slug else None,
    }


def search_marketplace(
    resources: list[dict[str, Any]],
    query: str,
    *,
    public_origin: str,
    max_results: int = 8,
    free_only: bool = False,
    max_price_usd: float | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    max_results = max(1, min(int(max_results), 20))
    q = str(query or "").strip()
    category_norm = str(category or "").strip().lower()

    ranked: list[tuple[float, dict[str, Any]]] = []
    for resource in resources or []:
        if not isinstance(resource, dict):
            continue

        if free_only and not _is_free(resource):
            continue

        price = _price_usd(resource)
        if max_price_usd is not None and price is not None and price > float(max_price_usd):
            continue

        if category_norm and category_norm not in _category(resource).lower():
            continue

        score = _score(resource, q)
        if q and score <= 0:
            continue
        ranked.append((score, resource))

    ranked.sort(
        key=lambda item: (
            -item[0],
            _price_usd(item[1]) if _price_usd(item[1]) is not None else math.inf,
            _title(item[1]).lower(),
        )
    )

    results = []
    for score, resource in ranked[:max_results]:
        item = summarize_resource(resource, public_origin)
        item["match_score"] = round(score, 2)
        results.append(item)

    return {
        "ok": True,
        "query": q,
        "filters": {
            "free_only": bool(free_only),
            "max_price_usd": max_price_usd,
            "category": category or None,
        },
        "count": len(results),
        "results": results,
        "next_step": (
            "Call vc_marketplace_details with a slug for full metadata. "
            "To execute a selected outcome, use its dedicated vc_* tool when available; "
            "otherwise call pay(slug=..., body=...)."
        ),
    }


def marketplace_details(
    resources: list[dict[str, Any]],
    slug: str,
    *,
    public_origin: str,
) -> dict[str, Any]:
    wanted = str(slug or "").strip()
    for resource in resources or []:
        if isinstance(resource, dict) and _slug(resource) == wanted:
            result = summarize_resource(resource, public_origin)
            result["metadata"] = {
                key: value
                for key, value in resource.items()
                if key not in {"secrets", "token", "api_key", "private_key"}
            }
            return {"ok": True, "resource": result}

    return {
        "ok": False,
        "error": "not_found",
        "slug": wanted,
        "hint": "Call vc_marketplace_search to discover valid Vibes-Coded resources.",
    }


def register_chatgpt_marketplace_tools(
    mcp,
    resources: list[dict[str, Any]],
    *,
    public_origin: str,
) -> None:
    @mcp.tool(annotations=READ_ONLY)
    def vc_marketplace_search(
        query: str = Field(
            description=(
                "What the user wants to accomplish, e.g. 'repair malformed JSON', "
                "'verify an agent completed a deployment', or 'search the web'."
            )
        ),
        max_results: int = Field(
            default=8,
            description="Maximum matches to return, from 1 to 20.",
        ),
        free_only: bool = Field(
            default=False,
            description="Only return resources that are free or explicitly marked free-tier.",
        ),
        max_price_usd: float | None = Field(
            default=None,
            description="Optional maximum listed USD price per call.",
        ),
        category: str | None = Field(
            default=None,
            description="Optional marketplace category filter.",
        ),
    ) -> str:
        """Search the Vibes-Coded marketplace for AI-agent tools and API outcomes.

        Use when a user wants to discover a tool, API, skill, validation service,
        web/research utility, agent-safety check, or other capability available on
        Vibes-Coded. Search by the user's actual task and return relevant listings.

        This tool only searches Vibes-Coded's bounded marketplace catalog. It does
        not execute a paid outcome, change user data, or search the general web.
        Prefer this before `pay` when the user has not already chosen a specific
        Vibes-Coded outcome.
        """
        result = search_marketplace(
            resources,
            query,
            public_origin=public_origin,
            max_results=max_results,
            free_only=free_only,
            max_price_usd=max_price_usd,
            category=category,
        )
        return json.dumps(result, indent=2, ensure_ascii=False, default=str)

    @mcp.tool(annotations=READ_ONLY)
    def vc_marketplace_details(
        slug: str = Field(
            description="Exact Vibes-Coded resource slug returned by vc_marketplace_search."
        )
    ) -> str:
        """Get details for one Vibes-Coded marketplace resource.

        Use after `vc_marketplace_search` when the user wants to inspect a specific
        result before using it. Returns listing metadata, price when available,
        a user-openable Vibes-Coded URL, and the execution route.

        Read-only and does not execute or purchase the resource.
        """
        return json.dumps(
            marketplace_details(resources, slug, public_origin=public_origin),
            indent=2,
            ensure_ascii=False,
            default=str,
        )
