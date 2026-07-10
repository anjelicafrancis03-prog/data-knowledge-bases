# SIT / Kanwas Fusion Workbench

Local operator workbench for reviewing and coordinating SIT, Kanwas, Stage10D evidence, and external-agent gate packets.

This is not a deployment backend and not a replacement for Harness authority. It is a controller-backed local workbench with explicit gates for:

- SIT status and local dev-server actions.
- Kanwas trial status and Docker actions.
- Stage10D evidence review.
- Local task packet creation.
- Dry-run adapter generation.
- Read-only Gate Center state for O-review and jcode promotion decisions.

## Current Safety Boundary

- No provider call is made by the UI or controller.
- No O1/O2/O3 review is dispatched without a separate exact approval phrase.
- `jcode` remains non-canonical and must not be launched from this workbench.
- Mutating routes are POST-only and require an HttpOnly same-origin workbench session cookie.
- When `strictOrigin` is enabled, mutating routes require an allowed Origin and workbench request header.
- Public read routes return sanitized summaries; same-origin workbench requests can read full local paths needed by the UI.
- High-risk local action groups are behind local feature flags.
- Local workstation paths live in `config.local.json`, which is ignored by Git.

## Local Run

Create a local config from the example, then run:

```powershell
python controller.py
```

Open:

```text
http://127.0.0.1:8766/index.html
```

## Configuration

- `config.example.json` is safe to commit and uses portable placeholder paths.
- `config.local.json` is machine-specific and ignored by Git.
- `FUSION_WORKBENCH_CONFIG` can point the controller at another local config file.

## Verification

Minimum local checks:

```powershell
python -m py_compile controller.py
python -m json.tool adapters/adapter-registry.json > $null
python -m json.tool config.example.json > $null
python tools/validate_workflow_gateway.py
pytest -q
```

Recommended security checks before push:

- No tracked file contains local absolute paths.
- No tracked file contains raw secrets, cookies, tokens, or browser session material.
- `config.local.json`, logs, runtime task packets, screenshots, evidence, reports, external inputs, ledgers, and caches are ignored.
- `/api/gates` still reports O-review as not sent and jcode as blocked/non-canonical.

## Workflow Gateway Artifacts

The Workflow Gateway layer is registry-only in this phase. It records runtime seats, bounded run-ledger entries, and read-only heartbeat intent without launching agents or exposing mutating routes.

- `agents/agent-runtimes.registry.json`
- `runs/workflow-run-ledger.jsonl`
- `runs/workflow-heartbeats.registry.json`
- `rooms/room-message-ledger.jsonl`
- `schemas/*.schema.json`
- `tools/validate_workflow_gateway.py`

Mutating gateway routes must not be exposed through Cloudflare Tunnel. Remote access requires a separate authenticated gateway and an L2 approval gate.

Room messages are directed by default. A room message must name `toSeats`; a broadcast is valid only when `visibility=room_broadcast` and explicit recipients are recorded. The room manifest stores summaries, not full implicit shared chat context.

Room runs also inherit the Site Workflow Console hard requirements: task packets, run manifest, evidence index, validator report, verification summary, protected-action ledger, and approval-manifest/hash evidence for protected actions. See `docs/site-workflow-contract-binding.md`.

The accepted GStack room operating decisions are recorded in `docs/gstack-room-operating-decisions.md` and enforced through `rooms/workflow-rooms.registry.json` plus `tools/validate_workflow_gateway.py`. Button inventory is intentionally deferred; the command-center area is reserved, but exact buttons are a separate design pass.

## First MR Goal

The first MR should be a local-hardening and security-boundary review only. It should not include deployment, real O-review dispatch, jcode promotion, or remote automation changes.

## Review Workflow

This project currently uses a hybrid review workflow:

- GitLab is the primary workbench, issue/MR surface, and GitLab Duo / Opus 4.8 review entry.
- GitHub Actions is the reliable CI green-light evidence while GitLab account verification or runner access is not fully available.
- Keep the GitLab MR and GitHub PR branches on the same commit.
- Treat GitLab pipeline/account-verification failures as platform gating unless the CI file itself is faulty.

See `docs/review-workflow.md` for the operating procedure.
