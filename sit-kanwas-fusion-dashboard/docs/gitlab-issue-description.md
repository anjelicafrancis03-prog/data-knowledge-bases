# SIT / Kanwas Fusion Workbench: Local Hardening And Review Track

## Goal

Build a practical local operator workbench that helps coordinate SIT, Kanwas, Stage10D evidence, task packets, and external-agent review gates without bypassing Harness authority or protected zones.

## Current Status

The workbench runs locally at:

```text
http://127.0.0.1:8766/index.html
```

Current gate state:

- Adapter registry: passed.
- O-review dispatch: approval-ready-not-sent.
- O-review sent manually: false.
- jcode seat: blocked-noncanonical.

## What This Issue Tracks

This issue tracks the first GitLab phase:

1. Local hardening.
2. Git-ready project structure.
3. Minimal CI plus boundary regression tests.
4. First MR for controller security-boundary review.
5. Follow-up fixes from GitLab Duo / Opus 4.8 review.

## Out Of Scope For This Issue

- Deployment.
- Real O-review dispatch.
- O1/O2/O3 provider calls.
- jcode launch or canonical promotion.
- Credential, cookie, browser-profile, MCP, Codex config, or startup-task mutation.

## Evidence

Primary external review packet and response:

- `opus-review-packet.gitlab-v2-20260614.md`
- `opus-4.8-response-20260614-2104.md`
- `delivery-log-20260614-2104.md`

Local workbench evidence:

- `README.md`
- `config.example.json`
- `.gitignore`
- `.gitlab-ci.yml`
- `tests/test_controller_boundaries.py`
- `docs/first-mr-description.md`

## Questions For Reviewers

1. Is the local controller boundary safe enough for a first MR?
2. Are the feature flags and committed defaults appropriately conservative?
3. Are public read routes sufficiently sanitized while preserving same-origin workbench usability?
4. What additional CI checks should be added before any real O-review or jcode promotion?
5. Are any evidence or provenance gaps still blocking the next phase?
