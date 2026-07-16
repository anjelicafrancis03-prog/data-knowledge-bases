# Codex Monitor HUD

This is the public, read-only companion page for the Windows Codex Monitor HUD.

## Data contract

`status.json` is a sanitized snapshot. It may contain profile names and health
states, but it must never contain API keys, auth files, local paths, command
output, logs, or private service URLs. The browser page treats a missing or
invalid snapshot as `unavailable`; it does not invent a live status.

The Windows HUD remains the control plane. `switch`, `test`, and `call` invoke
the local `F:\codex\codex-dashboard-api.ps1` wrapper and are intentionally not
exposed as public HTTP actions.

## Refreshing the snapshot

Export only the allowlisted fields from the local status wrapper, update
`status.json`, and review the diff before publishing. Do not run the existing
whole-worktree Wrangler fallback for this module until the portal allowlist and
manifest gate in Beads `codex-br4m.1` is complete.
