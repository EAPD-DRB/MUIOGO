# Contributing to MUIOGO

Thanks for contributing.

## Before starting

1. Read `README.md`, `docs/GSoC-2026.md`, `SUPPORT.md`, `docs/ARCHITECTURE.md`, and `docs/DOCS_POLICY.md`
2. Search existing issues and PRs before proposing implementation work
3. Create or reuse an issue before starting implementation work
4. Create a feature branch from `main`
5. Confirm acceptance criteria in the issue so review can be objective

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

## Issues and PRs

- Search existing issues and PRs first so we avoid duplicate work.
- For anything beyond a small fix, open an issue before implementation so scope and acceptance criteria are clear.
- Link the issue from your PR (`Closes #123`).
- Keep each PR scoped to one issue, or a tightly related set.
- If you find related work, link it so any overlap is visible — a quick reference is enough.

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

Small docs or typo-only PRs do not need a linked issue.

## Comments and code legibility

- Give modules with non-obvious responsibilities a short overview of their role
  and the data they own. Document public operations' inputs, outputs, and side
  effects when their names and signatures do not make these clear.
- Explain why a rule exists: scenario precedence, null inheritance, units and
  index order, compatibility requirements, cache validity, or concurrency.
  Avoid comments that merely repeat the next statement.
- Distinguish persisted entity IDs from display labels, source parameter files
  from generated inputs, and per-run artifacts from shared viewer caches.
- Keep comments next to the rule they explain. Update them with the code, and
  remove obsolete commented-out implementations; Git preserves their history.
- Use plain English and concrete examples for unfamiliar model conventions.
  State a helper's limits accurately; atomic replacement, for example, does not
  itself serialize concurrent writers.
- For a comments-only change, check syntax and inspect the executable diff.
  Run relevant existing regressions when shared modules are touched. Model
  optimization is not needed to validate comment changes.

See [the code reading map](docs/ARCHITECTURE.md#code-reading-map) for entry
points and the shared CLEWS table conventions.

## Definition of done

A task is done when:

1. Acceptance criteria in the issue are met
2. Code and docs are updated together
3. Reviewer feedback is resolved
4. Changes are merged to `EAPD-DRB/MUIOGO:main`
