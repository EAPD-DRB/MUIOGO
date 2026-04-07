#!/usr/bin/env python3
"""Validate PR intake structure against repository contribution policy."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable


ALLOWED_CLASSIFICATIONS = {
    "none",
    "duplicate",
    "alternative approach",
    "complementary follow-up",
    "narrower fix",
    "superseding",
}

ALLOWED_TRACKS = {
    "track: cross-platform",
    "track: og onboarding",
    "track: integration",
    "track: stability",
}

DOCS_ONLY_ALLOWED_EXACT = {
    "README.md",
    "SUPPORT.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
}
DOCS_ONLY_ALLOWED_PREFIXES = ("docs/",)

DOCS_ONLY_DISALLOWED_EXACT = {
    "CONTRIBUTING.md",
    "docs/MAINTAINER_TRIAGE.md",
}
DOCS_ONLY_DISALLOWED_PREFIXES = (".github/",)

PLACEHOLDER_VALUES = {
    "",
    "-",
    "tbd",
    "n/a",
    "none",
}

HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
REF_RE = re.compile(r"#(\d+)")
NONE_FOUND_RE = re.compile(r"\bnone found after search\b", re.IGNORECASE)


class ValidationError(Exception):
    """Raised when the PR intake structure is invalid."""


def api_get(url: str, token: str) -> tuple[object, dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "muiogo-pr-intake",
        },
    )
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            headers = {k: v for k, v in response.headers.items()}
            return data, headers
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise ValidationError(f"GitHub API request failed for {url}: {exc.code} {detail}") from exc


def parse_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        match = re.search(r"<([^>]+)>;\s*rel=\"([^\"]+)\"", part)
        if match and match.group(2) == "next":
            return match.group(1)
    return None


def fetch_paginated(url: str, token: str) -> list[object]:
    items: list[object] = []
    next_url: str | None = url
    while next_url:
        data, headers = api_get(next_url, token)
        if not isinstance(data, list):
            raise ValidationError(f"Expected a list from GitHub API for {next_url}")
        items.extend(data)
        next_url = parse_next_link(headers.get("Link"))
    return items


def extract_section(body: str, heading: str) -> str | None:
    lines = body.splitlines()
    target = heading.strip().lower()

    for idx, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match and match.group(1).strip().lower() == target:
            collected: list[str] = []
            for inner in lines[idx + 1 :]:
                if HEADING_RE.match(inner):
                    break
                collected.append(inner)
            return "\n".join(collected).strip()
    return None


def cleaned_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).strip().lower()


def looks_blank(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in PLACEHOLDER_VALUES


def path_is_docs_only_allowed(path: str) -> bool:
    if path in DOCS_ONLY_DISALLOWED_EXACT:
        return False
    if any(path.startswith(prefix) for prefix in DOCS_ONLY_DISALLOWED_PREFIXES):
        return False
    if path in DOCS_ONLY_ALLOWED_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in DOCS_ONLY_ALLOWED_PREFIXES)


def is_docs_exception_eligible(paths: Iterable[str]) -> bool:
    path_list = list(paths)
    return bool(path_list) and all(path_is_docs_only_allowed(path) for path in path_list)


def require_section(body: str, heading: str, errors: list[str], source: str) -> str | None:
    section = extract_section(body, heading)
    if section is None:
        errors.append(f"{source} is missing required section: {heading}")
        return None
    if not cleaned_lines(section):
        errors.append(f"{source} section is empty: {heading}")
        return None
    return section


def validate_issue_related_work(section: str, heading: str, errors: list[str]) -> None:
    if REF_RE.search(section) or NONE_FOUND_RE.search(section):
        return
    errors.append(
        f"Issue section '{heading}' must include issue/PR references like #123 or the phrase 'None found after search'"
    )


def validate_issue_overlap(section: str, errors: list[str]) -> None:
    normalized = normalize_text(section)
    if normalized not in ALLOWED_CLASSIFICATIONS:
        errors.append(
            "Issue section 'Overlap classification' must be one of: "
            + ", ".join(sorted(ALLOWED_CLASSIFICATIONS))
        )


def validate_issue_track(section: str, errors: list[str]) -> None:
    normalized = normalize_text(section)
    if normalized not in ALLOWED_TRACKS:
        errors.append(
            "Issue section 'Proposed track' must be one of: "
            + ", ".join(sorted(ALLOWED_TRACKS))
        )


def validate_issue_reason(section: str, heading: str, errors: list[str]) -> None:
    if looks_blank(section) or len(normalize_text(section)) < 10:
        errors.append(f"Issue section '{heading}' must contain a real explanation")


def find_linked_issue_numbers(section: str) -> list[int]:
    return [int(match) for match in REF_RE.findall(section)]


def select_linked_issue(repo: str, candidates: list[int], token: str) -> tuple[int, dict[str, object]]:
    for number in candidates:
        issue, _headers = api_get(f"https://api.github.com/repos/{repo}/issues/{number}", token)
        if not isinstance(issue, dict):
            continue
        if "pull_request" in issue:
            continue
        return number, issue
    raise ValidationError(
        "Linked issue section did not contain a valid issue reference. "
        "Issue references must point to issues, not PRs."
    )


def validate_pr_related_work(section: str, errors: list[str]) -> None:
    if REF_RE.search(section) or NONE_FOUND_RE.search(section):
        return
    errors.append(
        "PR section 'Existing related work reviewed' must include issue/PR references like #123 or the phrase 'None found after search'"
    )


def validate_pr_overlap(section: str, errors: list[str]) -> None:
    normalized = normalize_text(section)
    has_classification = any(cls in normalized for cls in ALLOWED_CLASSIFICATIONS)
    if not has_classification:
        errors.append(
            "PR section 'Overlap assessment' must include one overlap classification: "
            + ", ".join(sorted(ALLOWED_CLASSIFICATIONS))
        )
        return

    explanation_lines = []
    for line in cleaned_lines(section):
        if ":" in line:
            _prefix, suffix = line.split(":", 1)
            if suffix.strip():
                explanation_lines.append(suffix.strip())
        elif not line.startswith("-"):
            explanation_lines.append(line)

    meaningful = [line for line in explanation_lines if normalize_text(line) not in PLACEHOLDER_VALUES]
    if not meaningful or max(len(normalize_text(line)) for line in meaningful) < 8:
        errors.append("PR section 'Overlap assessment' must include real overlap details, not just placeholders")


def validate_pr_reason(section: str, errors: list[str]) -> None:
    if looks_blank(section) or len(normalize_text(section)) < 10:
        errors.append("PR section 'Why this PR should proceed' must contain a real explanation")


def validate_exception_rationale(body: str, errors: list[str]) -> None:
    section = extract_section(body, "Exception rationale")
    if section is None:
        errors.append("Docs/typo exception PRs must include the 'Exception rationale' section")
        return
    if looks_blank(section) or len(normalize_text(section)) < 10:
        errors.append("Docs/typo exception PRs must provide a non-empty exception rationale")


def validate_issue_body(issue_body: str, errors: list[str]) -> None:
    if not cleaned_lines(issue_body):
        errors.append("Linked issue body must not be empty")
        return

    related_issues = extract_section(issue_body, "Related issues reviewed")
    related_prs = extract_section(issue_body, "Related PRs reviewed")
    overlap = extract_section(issue_body, "Overlap classification")
    still_needed = extract_section(issue_body, "Why this issue is still needed")
    proposed_track = extract_section(issue_body, "Proposed track")

    if related_issues and not looks_blank(related_issues):
        validate_issue_related_work(related_issues, "Related issues reviewed", errors)
    if related_prs and not looks_blank(related_prs):
        validate_issue_related_work(related_prs, "Related PRs reviewed", errors)
    if overlap and not looks_blank(overlap):
        validate_issue_overlap(overlap, errors)
    if still_needed and not looks_blank(still_needed):
        validate_issue_reason(still_needed, "Why this issue is still needed", errors)
    if proposed_track and not looks_blank(proposed_track):
        validate_issue_track(proposed_track, errors)


def validate_pr_body(repo: str, pr_body: str, token: str, errors: list[str]) -> None:
    linked_issue = require_section(pr_body, "Linked issue", errors, "PR")
    related_work = require_section(pr_body, "Existing related work reviewed", errors, "PR")
    overlap = require_section(pr_body, "Overlap assessment", errors, "PR")
    why_proceed = require_section(pr_body, "Why this PR should proceed", errors, "PR")

    if linked_issue is None:
        return

    candidates = find_linked_issue_numbers(linked_issue)
    if not candidates:
        errors.append("PR section 'Linked issue' must include at least one issue reference such as Closes #123")
        return

    try:
        _issue_number, issue = select_linked_issue(repo, candidates, token)
    except ValidationError as exc:
        errors.append(str(exc))
        return

    issue_body = issue.get("body") or ""
    validate_issue_body(issue_body, errors)

    if related_work is not None:
        validate_pr_related_work(related_work, errors)
    if overlap is not None:
        validate_pr_overlap(overlap, errors)
    if why_proceed is not None:
        validate_pr_reason(why_proceed, errors)


def pr_has_linked_issue_reference(pr_body: str) -> bool:
    linked_issue = extract_section(pr_body, "Linked issue")
    if linked_issue is None:
        return False
    return bool(find_linked_issue_numbers(linked_issue))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PR intake structure")
    parser.add_argument("--repo", required=True, help="GitHub repository in owner/name form")
    parser.add_argument("--pr-number", required=True, type=int, help="Pull request number")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("FAIL: GITHUB_TOKEN is required")
        return 1

    pr_url = f"https://api.github.com/repos/{args.repo}/pulls/{args.pr_number}"
    pr, _headers = api_get(pr_url, token)
    if not isinstance(pr, dict):
        print(f"FAIL: Unexpected PR payload from {pr_url}")
        return 1

    files_url = f"https://api.github.com/repos/{args.repo}/pulls/{args.pr_number}/files?per_page=100"
    files = fetch_paginated(files_url, token)
    changed_paths = [item["filename"] for item in files if isinstance(item, dict) and "filename" in item]

    errors: list[str] = []
    pr_body = pr.get("body") or ""

    if pr_has_linked_issue_reference(pr_body):
        validate_pr_body(args.repo, pr_body, token, errors)
    elif is_docs_exception_eligible(changed_paths):
        validate_exception_rationale(pr_body, errors)
    else:
        validate_pr_body(args.repo, pr_body, token, errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("PASS: PR intake structure is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
