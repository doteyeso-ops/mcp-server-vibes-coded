from chatgpt_marketplace import marketplace_details, search_marketplace


RESOURCES = [
    {
        "id": "json-repair",
        "description": "Repair malformed JSON returned by LLMs.",
        "category": "developer tools",
        "price": {"currency": "USD", "amount": "0.02"},
        "url": "https://vibes-coded.com/api/v1/outcomes/json-repair",
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
    {
        "url": "https://vibes-coded.com/api/v1/outcomes/drift-guard",
        "description": "Guard against risky agent behavior and detect output drift.",
        "price_cents": 3,
        "pack": "agent safety",
    },
]


def test_search_prefers_semantic_title_slug_and_description_hits():
    result = search_marketplace(
        RESOURCES,
        "repair broken json",
        public_origin="https://vibes-coded.com",
    )
    assert result["count"] >= 1
    assert result["results"][0]["slug"] == "json-repair"
    assert result["results"][0]["title"] == "json-repair"


def test_slug_falls_back_to_outcome_url_leaf():
    result = search_marketplace(
        RESOURCES,
        "drift safety guard",
        public_origin="https://vibes-coded.com",
    )
    assert result["results"][0]["slug"] == "drift-guard"
    assert result["results"][0]["execution_tool"] == "vc_drift_guard"
    assert result["results"][0]["price_usd"] == 0.03


def test_free_only_filter():
    result = search_marketplace(
        RESOURCES,
        "schema json",
        public_origin="https://vibes-coded.com",
        free_only=True,
    )
    assert [x["slug"] for x in result["results"]] == ["schema-check"]


def test_max_price_filter_excludes_unknown_prices():
    result = search_marketplace(
        RESOURCES,
        "agent verify",
        public_origin="https://vibes-coded.com",
        max_price_usd=0.05,
    )
    assert all(x["price_usd"] is not None and x["price_usd"] <= 0.05 for x in result["results"])
    assert "agent-proof" not in [x["slug"] for x in result["results"]]


def test_details_returns_user_openable_url_and_execution_route():
    result = marketplace_details(
        RESOURCES,
        "agent-proof",
        public_origin="https://vibes-coded.com",
    )
    assert result["ok"] is True
    assert result["resource"]["url"] == "https://vibes-coded.com/outcomes/agent-proof"
    assert result["resource"]["execution_tool"] == "vc_agent_proof"
    assert result["resource"]["fallback_execution_tool"] == "pay"


def test_details_redacts_secret_like_metadata_keys():
    result = marketplace_details(
        [{"id": "secret-test", "api_token": "nope", "description": "test"}],
        "secret-test",
        public_origin="https://vibes-coded.com",
    )
    assert result["ok"] is True
    assert "api_token" not in result["resource"]["metadata"]


def test_details_not_found():
    result = marketplace_details(
        RESOURCES,
        "does-not-exist",
        public_origin="https://vibes-coded.com",
    )
    assert result["ok"] is False
    assert result["error"] == "not_found"
