"""Dependency-light deterministic scanner for agent skills and plugins."""

from __future__ import annotations

import hashlib
import re

MAX_CONTENT_CHARS = 200_000

_SKILL_RISK_RULES = (
    (
        "pipe_to_shell",
        "critical",
        50,
        re.compile(r"(?:curl|wget)\b[^\n|]{0,500}\|\s*(?:sudo\s+)?(?:ba)?sh\b", re.I),
        "Downloads content and pipes it directly into a shell.",
    ),
    (
        "private_key_access",
        "critical",
        35,
        re.compile(
            r"(?:~/|/home/[^/]+/|[A-Z]:\\\\Users\\\\[^\\]+\\\\)?\.ssh[/\\\\](?:id_rsa|id_ed25519)|BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY",
            re.I,
        ),
        "References private SSH or cryptographic key material.",
    ),
    (
        "secret_env_access",
        "high",
        35,
        re.compile(
            r"(?:os\.environ|getenv|process\.env)[^\n]{0,120}(?:API[_-]?KEY|SECRET|TOKEN|PASSWORD|PRIVATE[_-]?KEY)",
            re.I,
        ),
        "Reads a secret-bearing environment variable.",
    ),
    (
        "credential_file_access",
        "high",
        30,
        re.compile(
            r"(?:\.aws[/\\\\]credentials|\.config[/\\\\]gcloud|\.npmrc|\.pypirc|(?:^|[/\\\\])\.env\b)",
            re.I | re.M,
        ),
        "References a common credential file.",
    ),
    (
        "known_exfiltration_sink",
        "high",
        30,
        re.compile(
            r"\b(?:webhook\.site|requestbin\.(?:com|net)|pipedream\.net|ngrok(?:-free)?\.(?:app|io))\b",
            re.I,
        ),
        "References a commonly abused external collection endpoint.",
    ),
    (
        "shell_execution",
        "high",
        25,
        re.compile(
            r"\b(?:subprocess\.(?:run|call|Popen)|os\.system|child_process\.(?:exec|spawn)|execSync)\s*\(",
            re.I,
        ),
        "Executes an operating-system command.",
    ),
    (
        "destructive_command",
        "critical",
        50,
        re.compile(
            r"(?:\brm\s+-rf\b|\bdel\s+/[sqf]\b|\bformat\s+[a-z]:|Remove-Item\b[^\n]{0,80}-Recurse)",
            re.I,
        ),
        "Contains a destructive filesystem command.",
    ),
    (
        "encoded_payload",
        "medium",
        15,
        re.compile(r"\b(?:base64\.b64decode|atob|FromBase64String)\s*\(", re.I),
        "Decodes an embedded payload; review what executes after decoding.",
    ),
    (
        "package_install_hook",
        "medium",
        20,
        re.compile(r"[\"'](?:preinstall|postinstall|prepare)[\"']\s*:", re.I),
        "Defines an automatic package installation hook.",
    ),
)


def scan_skill_risk(content: str) -> dict:
    """Scan skill/plugin text for high-risk capability patterns."""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("content is empty")
    if len(content) > MAX_CONTENT_CHARS:
        raise ValueError(f"content exceeds {MAX_CONTENT_CHARS} characters")

    findings = []
    score = 0
    lines = content.splitlines()
    for rule_id, severity, weight, pattern, explanation in _SKILL_RISK_RULES:
        match = pattern.search(content)
        if not match:
            continue
        score += weight
        line_no = content.count("\n", 0, match.start()) + 1
        line = lines[line_no - 1].strip()[:180]
        findings.append(
            {
                "rule_id": rule_id,
                "severity": severity,
                "weight": weight,
                "line": line_no,
                "evidence": line,
                "explanation": explanation,
            }
        )

    score = min(score, 100)
    verdict = "block" if score >= 70 else "review" if score >= 30 else "allow"
    return {
        "ok": True,
        "scanner": "vibes-coded-skill-risk/1",
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "characters_scanned": len(content),
        "risk_score": score,
        "verdict": verdict,
        "findings": findings,
        "recommendation": (
            "Do not install or execute this skill until every critical/high finding is resolved."
            if verdict == "block"
            else "Require human review before installation."
            if verdict == "review"
            else "No known high-risk patterns found; provenance and signature checks are still recommended."
        ),
        "limitations": "Deterministic static scan; absence of findings is not proof of safety.",
    }


# Backward-compatible import used by the existing MCP server and tests.
_scan_skill_risk = scan_skill_risk
