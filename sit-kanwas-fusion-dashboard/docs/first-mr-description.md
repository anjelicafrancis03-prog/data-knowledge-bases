# MR: Local Hardening And Controller Security Boundary

## Summary

Prepare the SIT / Kanwas Fusion Workbench for independent review by turning it from a local HTML/controller artifact into a minimal Git-ready project.

## Changes

- Move workstation absolute paths out of `controller.py`.
- Add `config.example.json` for portable configuration.
- Keep `config.local.json` ignored and local-only.
- Add `.gitignore` for local config, logs, runtime tasks, screenshots, caches, and dependencies.
- Add minimal `.gitlab-ci.yml` checks plus controller boundary tests.
- Tighten mutating POST behavior with HttpOnly same-origin session cookies and strict Origin validation.
- Stop returning the operator token from `GET /api/session`.
- Sanitize public read routes so local paths, process command lines, task packet content, and adapter dry-run roots are reserved for same-origin workbench requests.
- Gate high-risk local action groups behind feature flags.
- Replace hardcoded local evidence links with controller whitelisted path actions.

## Explicit Non-Goals

- No deployment.
- No real O-review dispatch.
- No O1/O2/O3 provider call.
- No jcode launch.
- No jcode schema or registry promotion.
- No credential, cookie, browser-profile, MCP, Codex config, or startup-task mutation.

## Review Focus

1. Does the controller security boundary match the stated behavior?
2. Are mutating routes adequately protected by HttpOnly session, workbench header, and Origin checks?
3. Are high-risk local action groups disabled by default in committed config?
4. Is the Git ignore boundary sufficient to avoid leaking local paths, screenshots, logs, task packets, or local config?
5. Is the CI baseline plus pytest boundary coverage sufficient for a first hardening MR?

## Verification Performed

- `python -m py_compile controller.py`
- `python -m json.tool adapters/adapter-registry.json`
- `python -m json.tool config.example.json`
- `pytest -q`
- Prepared-file scan for local absolute paths and secret-like strings.
- HTTP boundary checks:
  - `/api/session` does not return a token
  - public `/api/status` strips config paths, file paths, adapter roots, and process command lines
  - public `/api/gates` strips file paths
  - `/api/tasks` without the workbench session is rejected with 403
  - same-origin workbench request with session cookie can still load status/tasks
- Browser navigation to `http://127.0.0.1:8766/index.html#gates`.

## Stop Conditions

Do not merge if:

- Any tracked file contains raw credentials, cookies, localStorage, API keys, or session material.
- `config.local.json` or runtime logs/task packets/screenshots are staged.
- A mutating route can bypass the workbench session or Origin checks.
- jcode becomes canonical without registry/schema/fixture review.
- O-review dispatch state changes from not-sent without explicit approval evidence.
