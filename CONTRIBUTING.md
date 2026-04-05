# Contributing to MUIOGO

Thanks for contributing.

## Before starting

1. Read `README.md`, `docs/GSoC-2026.md`, `docs/ARCHITECTURE.md`, and `docs/DOCS_POLICY.md`
2. Search existing issues and PRs before proposing implementation work
3. Create or reuse an issue before starting implementation work
4. Fill in the issue's required related-work fields so overlap is explicit
5. Create a feature branch from `main`
6. Confirm acceptance criteria in the issue so review can be objective

## Scope and repository boundaries

- This repo is downstream from `OSeMOSYS/MUIO` and must be deliverable on its own
- Do not block work here on upstream changes
- Upstream collaboration is encouraged, but this repo needs independent completion
- `MUIO-Mac` may be referenced, but `MUIOGO` targets platform-independent operation

## Issue prioritization and tracks

We use the following priority system:
- High: issues that should be worked on ASAP
- Medium: important issues
- Low: issues that may be important but that can wait

Priorities and track labels are assigned by maintainers.

Current tracks:
- `Track: Cross-Platform`
- `Track: OG Onboarding`
- `Track: Integration`
- `Track: Stability`

## Intake requirements

Most implementation work must start from an issue.

The issue must document:
- `Related issues reviewed`
- `Related PRs reviewed`
- `Overlap classification`
- `Why this issue is still needed`
- `Proposed track`

If you found no relevant existing work, write `None found after search`.

If overlapping work exists, explain why your issue is still needed and classify the overlap as one of:
- `none`
- `duplicate`
- `alternative approach`
- `complementary follow-up`
- `narrower fix`
- `superseding`

If no overlap exists, a short current justification is enough.

PRs should document:
- linked issue
- related work reviewed
- overlap assessment
- why the PR should proceed

The `pr-intake` workflow is advisory. If required structure is missing, it may apply the `needs-intake-fix` label so maintainers can follow up.

## Workflow

1. Start from an issue
2. Create a feature branch from `main`
3. Keep branch changes scoped to one issue or one tightly related set of issues
4. Include tests or validation steps whenever behavior changes
5. Update docs for any setup, architecture, or workflow change
6. Open a PR into `EAPD-DRB/MUIOGO:main` using the repository PR template

## Required branching rule

Every implementation contribution must use:
- an issue for scope and acceptance criteria
- a feature branch for implementation

Suggested branch format:
- `feature/<issue-number>-short-description`

## Communication model

This project uses event-driven updates (no weekly cadence requirement).
Post updates when one of these events occurs:
- Work started
- Blocked longer than 48 hours
- PR opened
- PR ready for review
- Milestone completed

## PR requirements

- Clear description of what changed and why
- Link to issue(s)
- Validation evidence:
  - test output, or
  - reproducible manual verification steps
- Docs updated when needed
- No unrelated refactors in the same PR
- PR target is `EAPD-DRB/MUIOGO:main` (not upstream `OSeMOSYS/MUIO`)

### Narrow docs and typo exception

For small docs or typo-only PRs, a linked issue may be skipped if the PR qualifies for the docs/typo exception.

This exception is narrow. It does not cover:
- workflows
- issue or PR templates
- governance or policy files
- `CONTRIBUTING.md`

Use the `Exception rationale` section in the PR template when claiming this exception.

Docs-only PRs may still use a linked issue instead of the exception path.

## Transition note

Existing open PRs and older linked issues from before the intake rollout are transitional and may be handled manually while the new intake guidance is phased in.

## Definition of done

A task is done when:

1. Acceptance criteria in the issue are met
2. Code and docs are updated together
3. Reviewer feedback is resolved
4. Changes are merged to `EAPD-DRB/MUIOGO:main`
