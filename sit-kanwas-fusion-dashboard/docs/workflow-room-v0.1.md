# Workflow Room v0.1

Status: draft-implemented
Created: 2026-06-15
Project: SIT / Kanwas Fusion Workbench

## Purpose

Workflow Room v0.1 implements the user's "Thread-as-Agent, Room-as-Workflow" idea as a local L1 coordination layer.

Standalone agents or threads keep their ordinary platform rules. When a thread, external review seat, browser lane, or future CLI adapter is named in a room packet, it also receives the room contract: role, evidence duties, allowed scope, forbidden actions, and stop conditions.

## Current Scope

This is an L1 packet-room implementation.

It can:

- store a workflow-room registry under `rooms/workflow-rooms.registry.json`;
- expose room state through the local controller at `/api/rooms`;
- project room membership and contract into the workbench UI;
- generate a local kickoff task packet through `/api/room/<id>/kickoff`;
- keep room work tied to task packets, manifests, evidence indexes, and review outputs.
- bind every room run to the Site Workflow Console evidence and approval contract.

It cannot:

- dispatch live agents automatically;
- call O1/O2/O3, Claude, Codex, Gemini, Qoder, jcode, or browser automation;
- read credentials, cookies, browser state, or raw provider logs;
- mutate Codex config, MCP registration, startup tasks, deployment, Git merge, or publishing state;
- treat UI state as durable truth.

## Authority Split

```text
Harness files = durable truth and authority
Workflow room = membership and contract projection
Task packets = bounded work units
External seats = reviewer or analyst only at L1
Kanwas/workbench = human-facing operation surface
Polynoia/jcode/CLI adapters = future execution-kernel candidates, not authority
```

## Room Entry Rule

A seat has two modes:

- `normalMode`: what it follows when it is acting as a standalone thread or ordinary tool.
- `roomMode`: what it follows after it is included in a room packet.

The room does not erase the normal mode. It adds project-level obligations for this run.

The front-end join interaction should feel like adding a participant to a chat room, but the backend must treat it as a control-layer action. Only control or the current orchestrator may pull an agent into a room. The system must create and validate a room join packet, assign a role, record the audit event, and then switch the seat into room mode.

Phase 1 keeps orchestrator upgrades Codex-only. Non-Codex seats can act as `domain_lead` for a bounded domain under the orchestrator, but they cannot merge, close the room, override packets, or change authority.

One agent may belong to only one active room at a time. Moving rooms requires a room exit packet with one of: `resume_normal`, `archive`, or `detached_handoff`.

## Site Workflow Binding

Joining a room also activates the Site Workflow Console contract. This is a hard requirement, not an optional reference.

The room must preserve:

- normal thread rules, local AGENTS instructions, role rules, credential boundaries, and handoff/checkpoint duties;
- Harness files as the durable source of truth;
- Site Workflow Console gates for approval, protected actions, evidence, validation, and run-id namespacing;
- Room-specific task packets, directed messages, worktree or branch policy, and exit packets.

The workbench and Kanwas may display the room state, but UI state, localStorage, screenshots, and canvas layout are not truth sources. Truth belongs in Harness files, manifests, evidence indexes, Git, CI, saved review outputs, and validated ledgers.

Required room-run evidence follows `docs/site-workflow-contract-binding.md`.

## Message Visibility Rule

Room messages are not implicit broadcasts.

Every room message must record:

- `fromSeat`
- `toSeats`
- `ccSeats`
- `visibility`
- `messageType`
- `taskPacketId` or equivalent packet reference
- `roomPacketId` or equivalent packet reference
- `timestamp`
- `summary`
- `evidenceLinks` when applicable
- `manifestVisibility`

Default visibility is direct. A sender cannot assume that every member saw a message unless `visibility=room_broadcast` and the target seats are explicitly listed. The room manifest stores summary facts and routing references; it is not a full shared transcript or shared hidden context.

`ccSeats` is visibility only, not assignment. If `toSeats` is empty, nobody receives the task. Such a message may be stored as a draft or audit log, but no agent should execute it.

## Command Center First Screen

The default room surface is a control command center, not the full chat stream. It must show room status, agent seats, current tasks, pending approvals, latest evidence, and a reserved command area. The full chat flow remains available, with filters for direct, cc, broadcast, approval, evidence, task, and system messages.

Agent seat cards must expose: name, role, provider/model, status, current task, branch/worktree, last activity time, and latest evidence. Allowed status values are `available`, `busy`, `waiting_user`, `blocked`, `archived`, and `offline`.

The exact command button list is deferred to the next design pass.

## Coding And Integration Rule

Writing agents require a task packet, their own branch/worktree, allowed file scope, tests to run, and evidence level before editing. Agent branches follow `room/<room_id>/<agent_id>/<task_slug>`. Integration branches follow `integration/<room_id>/<task_slug>`.

A coding agent may commit to its own branch only after its required tests and evidence are satisfied. It cannot merge, push main, close MR/PR, or mark the task complete without required evidence. The orchestrator owns integration and integration verification.

Clarifications route through `clarificationTarget` when present. Otherwise product choices go to the user, permission/security/fact conflicts go to control, technical implementation questions go to the orchestrator, and domain questions go to the relevant domain lead.

If an agent lacks permission, it must create a permission request and may include a read-only patch proposal. It must not continue by guessing authority.

## Close And Memory Rule

Only the user can finally close a room. The orchestrator may submit a close request with final verdict, completed items, open items, test/evidence summary, remaining risks, and handoff/archive path.

Room memory is allowed only with scoped access, sensitive filtering, and auditable sources. Ordinary members receive summaries. Control, the orchestrator, and authorized reviewers may receive permissioned full source chains.

## First Room

The first implemented room is `sit-kanwas-fusion-room`.

Current members:

- `codex-control`: controller/evidence owner.
- `browser-lane`: planned screenshot and UI evidence lane.
- `o3-review`: packet-ready closed-report review lane.
- `jcode-candidate`: non-canonical review-only future adapter lane.

## L2 Gate

Before any room member can become a live worker, a separate L2 gate must define:

- runtime wrapper or sandbox boundary;
- explicit command and working-directory policy;
- allowed reads and allowed writes;
- protected-zone negative fixtures;
- baseline hash and post-run diff checks;
- rollback commands;
- exact human approval phrase;
- saved evidence and review output.

L2 must also inherit the Site Workflow Console protected-action gate: approval manifest, SHA256 sidecar, approval evidence, validation report, verification summary, changed-file hashes, protected-action ledger, and run-id namespaced outputs. Site-direct CLI remains forbidden unless a separate approved contract explicitly changes that boundary.

Room v0.1 deliberately stops before this line.
