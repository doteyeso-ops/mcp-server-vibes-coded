import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_server import _reconcile_skill_scan_reports


class SkillScanConsensusTests(unittest.TestCase):
    def test_unanimous_allow_reports_allow_with_full_agreement(self):
        result = _reconcile_skill_scan_reports(
            [
                {"scanner": "alpha", "verdict": "allow", "risk_score": 5, "findings": []},
                {"scanner": "beta", "verdict": "allow", "risk_score": 12, "findings": []},
            ]
        )

        self.assertEqual(result["conservative_verdict"], "allow")
        self.assertEqual(result["agreement_percent"], 100.0)
        self.assertTrue(result["unanimous"])
        self.assertEqual(result["conflicts"], [])

    def test_disagreement_preserves_block_and_surfaces_conflict(self):
        result = _reconcile_skill_scan_reports(
            [
                {"scanner": "alpha", "verdict": "allow", "risk_score": 8, "findings": []},
                {
                    "scanner": "beta",
                    "verdict": "block",
                    "risk_score": 91,
                    "findings": [{"rule_id": "credential-harvest"}],
                },
                {
                    "scanner": "gamma",
                    "verdict": "review",
                    "risk_score": 48,
                    "findings": [{"id": "network-exfiltration"}],
                },
            ]
        )

        self.assertEqual(result["conservative_verdict"], "block")
        self.assertEqual(result["agreement_percent"], 33.3)
        self.assertFalse(result["unanimous"])
        self.assertEqual(len(result["conflicts"]), 1)
        self.assertEqual(
            result["combined_finding_ids"],
            ["credential-harvest", "network-exfiltration"],
        )
        self.assertEqual(len(result["evidence_sha256"]), 64)

    def test_requires_two_to_ten_named_reports(self):
        with self.assertRaisesRegex(ValueError, "2 to 10"):
            _reconcile_skill_scan_reports([{"scanner": "only", "verdict": "allow"}])
        with self.assertRaisesRegex(ValueError, "scanner"):
            _reconcile_skill_scan_reports(
                [{"scanner": "alpha", "verdict": "allow"}, {"verdict": "review"}]
            )
        with self.assertRaisesRegex(ValueError, "verdict"):
            _reconcile_skill_scan_reports(
                [
                    {"scanner": "alpha", "verdict": "allow"},
                    {"scanner": "beta", "verdict": "unknown"},
                ]
            )


if __name__ == "__main__":
    unittest.main()
