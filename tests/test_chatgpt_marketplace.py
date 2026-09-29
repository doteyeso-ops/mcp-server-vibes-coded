from chatgpt_marketplace import marketplace_details, search_marketplace


RESOURCES = [
    {
        "id": "json-repair",
        "title": "JSON Repair",
        "description": "Repair malformed JSON returned by LLMs.",
        "category": "developer tools",
        "price_usd": "0.02",
    },
    {
        "id": "agent-proof",
        "title": "Agent Proof",
        "description": "Verify an agent completion claim against external state.",
        "category": "agent safety",
        "price": {"amount": 0.25},
    },
    {
        "id": "schema-check",
        "title": "Schema Check",
        "description": "Validate JSON payloads against a schema.",
        "category": "developer tools",
        "price_usd": 0,
        "free": True,
    },
]


def test_search_prefers_semantic_title_and_description_hits():
    result = search_marketplace(
        RESOURCES,
        "repair broken json",
        public_origin="https://vibes-coded.com",
    )
    assert result["count"] >= 1
    assert result["results"][0]["slug"] == "json-repair"


def test_free_only_filter():
    result = search_marketplace(
        RESOURCES,
        "schema json",
        public_origin="https://vibes-coded.com",
        free_only=True,
    )
    assert [x["slug"] for x in result["results"]] == ["schema-check"]


def test_max_price_filter():
    result = search_marketplace(
        RESOURCES,
        "agent verify",
        public_origin="https://vibes-coded.com",
        max_price_usd=0.05,
    )
    assert all((x["price_usd"] or 0) <= 0.05 for x in result["results"])
    assert "agent-proof" not in [x["slug"] for x in result["results"]]


def test_details_returns_user_openable_url():
    result = marketplace_details(
        RESOURCES,
        "agent-proof",
        public_origin="https://vibes-coded.com",
    )
    assert result["ok"] is True
    assert result["resource"]["url"] == "https://vibes-coded.com/outcomes/agent-proof"
    assert result["resource"]["execution_tool"] == "pay"


def test_details_not_found():
    result = marketplace_details(
        RESOURCES,
        "does-not-exist",
        public_origin="https://vibes-coded.com",
    )
    assert result["ok"] is False
    assert result["error"] == "not_found"
