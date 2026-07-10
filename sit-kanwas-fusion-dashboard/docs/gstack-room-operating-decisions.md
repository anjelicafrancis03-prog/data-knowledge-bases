# GStack Room Operating Decisions

Status: accepted for Room v0.1
Created: 2026-06-15
Scope: decisions 1-19 from the user/control GStack room-design session

## Purpose

This file records the first accepted operating rules for the SIT / Kanwas Workflow Room. It turns the user-confirmed GStack decisions into a durable project contract before the command-button design is finalized.

Button layout and exact button inventory are intentionally deferred. The first screen must reserve a command center surface, but the button set will be decided in the next design pass.

## Accepted Rules

1. Room first screen is a control command center for the user/control seat, not a long chat stream.
2. Agent seat cards have fixed fields: name, role, provider/model, status, current task, branch/worktree, last activity time, and latest evidence.
3. Allowed agent statuses are `available`, `busy`, `waiting_user`, `blocked`, `archived`, and `offline`.
4. Messages are not implicitly delivered. Empty `toSeats` means no delivery.
5. Only explicit `room_broadcast` counts as a room-wide notification.
6. `ccSeats` is visibility only, not task assignment.
7. Agents keep normal thread/platform rules until a valid room join packet places them into room mode.
8. The front-end join interaction should feel as simple as adding someone to a chat room, while the backend creates and validates the required packet.
9. Pulling a member into a room is a control-layer action. Only control or the current orchestrator can do it.
10. Joining requires an explicit role. The allowed role set is `orchestrator`, `coder`, `reviewer`, `browser`, `search`, `ops`, `context`, `tools`, and `observer`.
11. One agent can be in only one active room at a time. Changing rooms requires an exit packet.
12. In phase 1, only Codex threads can be upgraded from normal thread mode to orchestrator.
13. Non-Codex agents can be `domain_lead` under the orchestrator, but cannot merge, close rooms, override packets, or change authority.
14. Writing agents require their own branch/worktree by default.
15. Agent branch names use `room/<room_id>/<agent_id>/<task_slug>`. Integration branches use `integration/<room_id>/<task_slug>`.
16. Writing agents may commit to their own branch after task-packet tests and evidence are satisfied. They cannot merge, push main, close MR/PR, or mark completion without required evidence.
17. Test responsibility is layered: agent task tests, orchestrator integration tests, then a review evidence summary.
18. Clarification routing follows `clarificationTarget` first, then product questions to the user, permission/security/fact conflicts to control, implementation questions to the orchestrator, and domain questions to the domain lead.
19. Permission gaps produce a permission request and may include a read-only patch proposal. Agents must not continue by guessing authority.
20. Evidence defaults to summary with links, while audit mode exposes the full chain.
21. Only the user can finally close a room. The orchestrator may submit a close request with verdict, completed/open items, evidence summary, risks, and handoff path.
22. Room memory is allowed only with scoped access, sensitive filtering, and auditable sources.
23. Complete room chat logs are preserved as structured records with routable recipients, packet references, timestamps, and evidence links.
24. Room work must inherit the existing SITE workflow contract, protected zones, authority layer, task packet, evidence manifest, review packet, approval gate, and handoff checkpoint rules.

## Implementation Binding

The machine-readable binding lives in:

- `rooms/workflow-rooms.registry.json` under `siteWorkflowBinding.gstackRoomModelPolicy`
- `tools/validate_workflow_gateway.py`
- `tests/test_workflow_gateway_artifacts.py`

The validator must reject any future registry state that weakens these rules.
