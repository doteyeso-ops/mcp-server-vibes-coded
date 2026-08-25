"""Local runner for the Vibes-Coded Agent Skill Risk Scan GitHub Action."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skill_risk import MAX_CONTENT_CHARS, scan_skill_risk

SUPPORTED_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".py",
    ".sh",
    ".bash",
    ".ps1",
}
SUPPORTED_NAMES = {".env", ".npmrc", ".pypirc", "Dockerfile"}
SKIP_DIRECTORIES = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}
VERDICT_RANK = {"allow": 0, "review": 1, "block": 2}


def _supported_files(path: Path) -> list[Path]:
    if path.is_file():
        candidates = [path]
        base = path.parent
    elif path.is_dir():
        base = path
        candidates = [
            item
            for item in path.rglob("*")
            if item.is_file()
            and not any(part in SKIP_DIRECTORIES for part in item.relative_to(base).parts[:-1])
        ]
    else:
        raise ValueError(f"scan path does not exist: {path}")

    supported = [
        item
        for item in candidates
        if item.suffix.lower() in SUPPORTED_SUFFIXES or item.name in SUPPORTED_NAMES
    ]
    return sorted(supported, key=lambda item: item.relative_to(base).as_posix().casefold())


def scan_path(path: str | Path) -> dict:
    """Scan one file or a directory tree and return a deterministic report."""
    target = Path(path).resolve()
    files = _supported_files(target)
    if not files:
        raise ValueError("no supported files found to scan")

    base = target if target.is_dir() else target.parent
    chunks: list[str] = []
    ranges: list[tuple[int, int, str]] = []
    line_cursor = 1
    total_characters = 0

    for item in files:
        relative = item.relative_to(base).as_posix()
        try:
            content = item.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        header = f"# FILE: {relative}\n"
        chunk = header + content
        if not chunk.endswith("\n"):
            chunk += "\n"
        total_characters += len(chunk)
        if total_characters > MAX_CONTENT_CHARS:
            raise ValueError(f"combined supported input exceeds {MAX_CONTENT_CHARS} characters")
        start = line_cursor + 1
        end = line_cursor + chunk.count("\n")
        ranges.append((start, end, relative))
        chunks.append(chunk)
        line_cursor = end + 1

    if not chunks:
        raise ValueError("no supported UTF-8 files found to scan")

    report = scan_skill_risk("\n".join(chunks))
    report["files_scanned"] = [item.relative_to(base).as_posix() for item in files]
    report["file_count"] = len(report["files_scanned"])
    for finding in report["findings"]:
        global_line = int(finding["line"])
        for start, end, relative in ranges:
            if start <= global_line <= end:
                finding["source_file"] = relative
                finding["source_line"] = global_line - start + 1
                break
    return report


def should_fail(verdict: str, fail_on: str) -> bool:
    """Return whether a verdict reaches the configured failure threshold."""
    threshold = str(fail_on).strip().lower()
    if threshold == "none":
        return False
    if threshold not in VERDICT_RANK:
        raise ValueError("fail threshold must be one of: none, allow, review, block")
    normalized_verdict = str(verdict).strip().lower()
    if normalized_verdict not in VERDICT_RANK:
        raise ValueError("verdict must be one of: allow, review, block")
    return VERDICT_RANK[normalized_verdict] >= VERDICT_RANK[threshold]


def _append_file(path_value: str | None, content: str) -> None:
    if not path_value:
        return
    with Path(path_value).open("a", encoding="utf-8") as handle:
        handle.write(content)


def _write_summary(report: dict) -> None:
    lines = [
        "## Vibes-Coded Agent Skill Risk Scan",
        "",
        f"- Verdict: **{report['verdict'].upper()}**",
        f"- Risk score: **{report['risk_score']}/100**",
        f"- Files scanned: **{report['file_count']}**",
        f"- Findings: **{len(report['findings'])}**",
        "",
    ]
    if report["findings"]:
        lines += ["| Severity | Rule | File | Line |", "|---|---|---|---:|"]
        for item in report["findings"]:
            lines.append(
                f"| {item['severity']} | `{item['rule_id']}` | "
                f"`{item.get('source_file', 'combined input')}` | {item.get('source_line', item['line'])} |"
            )
    else:
        lines.append("No known high-risk patterns were found. This is not proof of safety.")
    _append_file(os.getenv("GITHUB_STEP_SUMMARY"), "\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=".", help="File or directory to scan")
    parser.add_argument("--report", default="vibes-skill-risk-report.json", help="JSON report path")
    parser.add_argument("--fail-on", default="block", help="none, allow, review, or block")
    args = parser.parse_args(argv)

    try:
        report = scan_path(args.path)
        failure = should_fail(report["verdict"], args.fail_on)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report_path = Path(args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _append_file(
        os.getenv("GITHUB_OUTPUT"),
        f"verdict={report['verdict']}\nrisk_score={report['risk_score']}\nreport_path={report_path.as_posix()}\n",
    )
    _write_summary(report)
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "risk_score": report["risk_score"],
                "files_scanned": report["file_count"],
                "findings": len(report["findings"]),
                "report_path": report_path.as_posix(),
            }
        )
    )
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
