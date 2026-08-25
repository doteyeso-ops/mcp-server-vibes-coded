import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_server import _provider_gateway_authorized


class ProviderGatewayAuthTests(unittest.TestCase):
    def test_accepts_rapidapi_or_provider_header_with_exact_secret(self):
        self.assertTrue(
            _provider_gateway_authorized(
                {"X-RapidAPI-Proxy-Secret": "secret-123"}, "secret-123"
            )
        )
        self.assertTrue(
            _provider_gateway_authorized(
                {"x-vibes-provider-key": "secret-123"}, "secret-123"
            )
        )

    def test_rejects_missing_wrong_or_unconfigured_secret(self):
        self.assertFalse(_provider_gateway_authorized({}, "secret-123"))
        self.assertFalse(
            _provider_gateway_authorized(
                {"X-RapidAPI-Proxy-Secret": "wrong"}, "secret-123"
            )
        )
        self.assertFalse(
            _provider_gateway_authorized(
                {"X-RapidAPI-Proxy-Secret": "anything"}, ""
            )
        )


if __name__ == "__main__":
    unittest.main()
