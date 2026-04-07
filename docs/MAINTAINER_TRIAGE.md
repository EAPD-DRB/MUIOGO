# Maintainer Triage Guide

This document defines the contribution-intake workflow introduced for issue-first, overlap-aware implementation work.

## Purpose

The intake system exists to reduce duplicate work, clarify scope before code is written, and keep review attention on the highest-signal items.

Automation checks structure only:
- linked issue exists
- required issue sections are present
- required PR sections are present

If structure is missing, automation may apply the `needs-intake-fix` label to the PR.

Maintainers still decide whether the proposal is correct, useful, or merge-ready.

## What to review on new implementation issues

Confirm that the issue documents:
- `Related issues reviewed`
- `Related PRs reviewed`
- `Overlap classification`
- `Why this issue is still needed`
- `Proposed track`

If related-work sections are weak but present, request clarification rather than bypassing the structure.

If the issue is clearly duplicate or superseded, close or consolidate it rather than carrying parallel implementation work.

## Overlap classifications

Use these overlap terms consistently:
- `none`: no relevant overlapping work found
- `duplicate`: same problem and same intended fix as an existing issue or PR
- `alternative approach`: same problem, materially different solution path
- `complementary follow-up`: separate work that depends on or extends existing work
- `narrower fix`: intentionally smaller or more targeted than a broader open item
- `superseding`: intended to replace an older issue or PR as the canonical path

## Handling overlap

- Duplicate: point contributors to the canonical issue or PR and close the duplicate
- Alternative approach: keep only if there is a real design choice to evaluate
- Complementary follow-up: keep separate, but explicitly link the dependency chain
- Narrower fix: allow if the narrower path is more actionable than the broader one
- Superseding: make the replacement explicit in comments and close the older item when appropriate

## Tracks

Tracks are maintainer-assigned triage metadata.

- `Track: Cross-Platform`
  Cross-platform install, startup, path, and runtime compatibility work

- `Track: OG Onboarding`
  First-run UX, contributor/user guidance, onboarding flow, and related docs

- `Track: Integration`
  OG-Core, coupled workflows, orchestration, and integration interfaces

- `Track: Stability`
  Run safety, async execution design, shared-state integrity, run identity and status tracking, and runtime robustness

## Stability lanes

For now, Stability lanes are an internal triage vocabulary only.

- `Safety Guardrails`
  Narrow fixes that make the current synchronous design safer without redesigning execution flow

- `Async Architecture`
  Non-blocking job execution, polling, cancellation, and task orchestration proposals

- `Supporting Infrastructure`
  Run identity, atomic status tracking, shared metadata safety, and run-level observability work

## Transitional policy

Open PRs that predate the intake rollout are transitional:
- the new `pr-intake` workflow may run on them
- maintainers may clean them up manually
- they are not retroactively required to match the new structure before the rollout is complete

Once the queue is cleaned up, new or substantially updated PRs should follow the full intake format. The intake workflow is advisory and does not replace maintainer judgment.
