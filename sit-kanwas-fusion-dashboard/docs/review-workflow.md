# Review Workflow

This project uses a hybrid workflow until GitLab CI and GitLab Duo flow permissions are fully unblocked.

## Source Of Truth

- GitLab project: `https://gitlab.com/dgsdgg-group/sit-kanwas-fusion-workbench`
- GitLab MR: `https://gitlab.com/dgsdgg-group/sit-kanwas-fusion-workbench/-/merge_requests/1`
- GitHub PR mirror: `https://github.com/anjelicafrancis03-prog/sit-kanwas-fusion-workbench/pull/1`
- Branch: `harden-controller-boundary`

## Default Operating Mode

1. Make scoped local changes.
2. Run local verification:

```powershell
python -m py_compile controller.py
python -m json.tool adapters/adapter-registry.json > $null
python -m json.tool config.example.json > $null
python -m json.tool rooms/workflow-rooms.registry.json > $null
python tools/validate_workflow_gateway.py
pytest -q
git diff --check
```

3. Push the same branch to GitLab and GitHub.
4. Use GitLab MR as the primary review object.
5. Use GitLab Duo / Opus 4.8 from the GitLab MR page for architecture and safety review.
6. Use GitHub Actions as the reliable CI evidence while GitLab pipeline execution is gated.
7. Save review output and evidence under `F:\codex\reports\workflow-room-opus-review-20260615` or the current dated review package.

## Current Constraint

GitLab may show account verification or permission gating before pipelines or automated `code_review` flows can run. Until that is fixed, a red or blocked GitLab pipeline is not by itself a code defect. Confirm code health from:

- local verification results,
- GitHub Actions for the same commit,
- GitLab Duo / Opus MR review comments.

## Review Boundary

GitLab Duo / Opus review should focus on:

- Harness files vs Workflow Room vs task packet vs UI authority split.
- Protected zones: no provider calls, CLI/jcode launches, credential/browser/config/startup/deploy/merge/publish mutation.
- Session, Origin, and mutating-route guards.
- Room kickoff task-packet safety.
- Whether the change is safe as an L1 coordination surface.
- Whether Workflow Gateway artifacts remain schema-validated, read-only at L1, and never expose mutating routes through Cloudflare Tunnel.
- Whether room messages are explicitly addressed rather than treated as implicit broadcasts; manifest entries should remain summary-only unless a separate packet permits fuller context.

Do not treat the workbench UI as durable authority. Durable project state belongs in Git, MR comments, reports, evidence files, and Harness documents.
