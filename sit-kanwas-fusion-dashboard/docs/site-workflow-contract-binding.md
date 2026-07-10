# Site Workflow Contract Binding

Status: hard requirement
Created: 2026-06-15
Project: SIT / Kanwas Fusion Workbench

## Purpose

Room work must inherit the Site Workflow Console rules that were proven in the earlier SIT/site phases. A room is not a looser parallel workflow. It is normal thread rules plus the Site workflow contract plus the room overlay.

## Binding Rule

When a thread or external seat is added to a room packet, the active rule stack becomes:

1. Codex/platform safety rules.
2. Local AGENTS and durable credential rules.
3. The thread's normal role contract.
4. Site Workflow Console authority, approval, manifest, evidence, and validation requirements.
5. Room overlay rules: directed messages, room entry packet, task packet, worktree/branch policy, and exit packet.

The room does not reset ordinary thread rules. It adds stricter project workflow obligations.

## Room Policy Decisions

The current room policy follows the user's approved C/C/C decisions:

- Packet generation: the inviter may draft the room entry or task packet, but control must validate it before the seat is considered joined.
- Permission inheritance: normal platform capabilities remain available, but room write and execution scope is controlled only by the room packet.
- Evidence display: the workbench must support daily and audit modes. Daily mode may show the final conclusion first, but audit mode must expose the full manifest, evidence, validator, approval, and ledger trail.

## Hard Requirements

Every room run must record:

- route decision or route trace when Harness routing is relevant;
- room entry packet and task packet paths;
- run manifest path;
- evidence index path;
- validator report path;
- verification summary path or explicit not-run reason;
- bridge trace path or explicit mock-only/no-bridge note;
- output artifact paths under a run-id namespace;
- protected-action ledger path, even if it records no protected action;
- final status and stop condition.

Closed review tasks additionally require:

- bounded review packet;
- captured review response;
- delivery log or MR/issue comment reference;
- local saved review output path.

Any write, execution, deployment, browser-state action, provider call, merge, publish, config/MCP/startup mutation, credential access, or other protected action additionally requires:

- exact human approval text;
- approval manifest;
- approval-manifest SHA256 sidecar;
- approval evidence;
- hash-bound approved text;
- changed-file hashes or explicit no-file-change proof;
- negative fixture or validator coverage for the protected boundary.

## Fixed Boundaries

- Harness files are durable authority.
- Workbench and Kanwas are operator/projection surfaces, not authority.
- Site direct CLI remains blocked.
- Terminal worker execution requires a fresh approval manifest.
- `includeMcpLive` defaults to false.
- UI state, localStorage, screenshots, and chat memory cannot be the only source of truth.
- Missing artifacts, failed validation, failed task tests, protected-zone diffs, or partial outputs block completion.

## Evidence Levels

Room tasks must declare an evidence level:

- `light_readonly`: read-only status, question answering, or simple local inspection. Requires task packet, manifest entry, evidence note, and stop condition.
- `review_packet`: closed review or Opus/Duo/O-seat review. Requires task packet, review packet, captured response, manifest entry, evidence index, and verification note.
- `full_site_bundle`: writing, local execution, browser evidence, search/research with durable impact, or multi-agent implementation. Requires the full room-run evidence bundle.
- `protected_execution`: any protected action. Requires the full site bundle plus approval manifest, SHA256 sidecar, approval evidence, changed-file hashes, and protected-action ledger.

If a task is ambiguous, treat it as the stricter level until the packet is clarified.

## Completion Gate

A room task cannot be marked complete unless its declared evidence level is satisfied. If a required artifact is missing, the correct status is `blocked` or `partial`, not `complete`.

## Workbench Display Gate

The UI may optimize for command speed, but it must not hide the evidence model from the workflow:

- daily mode: final conclusion, current status, operation buttons, and compact evidence links;
- audit mode: complete manifest, evidence index, validator report, approval artifacts, protected-action ledger, branch/worktree/commit status, and review outputs;
- any final conclusion must link back to the artifact paths that justify it.

## Command Surface Policy

The workbench command surface follows the user's approved gStack recommendation:

- first screen: control command center with room status, agent seats, current tasks, pending approvals, latest evidence, and a reserved command area;
- room composer: no implicit recipient. If `toSeats` is empty, nobody receives the message; the UI must prompt for recipients or explicit broadcast;
- seat card: always show name, role, provider/model, status, current task, branch/worktree, last activity time, and latest evidence;
- new thread: starts in normal thread mode by default; joining a room requires an explicit join action and generated packet;
- approval display: approval requests appear in the chat context and in a separate approval queue.
- full chat stream: preserved and filterable, but not the default first-screen experience.

These UI choices must not weaken the Site Workflow Console authority, evidence, or approval gates.

The exact command button set is intentionally deferred. The first-screen command area is required, but button inventory must be decided in a separate design pass.

## Multi-Agent Coding Policy

Multi-agent implementation work follows the user's approved C/C/B/C/C/C decisions:

- orchestrator: default is Codex control. In phase 1, only Codex threads can be upgraded from normal thread mode to orchestrator;
- domain lead: non-Codex seats may be domain leads under the orchestrator, but cannot merge, close rooms, override packets, or change authority;
- coding preflight: a writing agent must have a task packet, branch/worktree, allowed files, tests to run, and evidence level before editing;
- branch policy: agent branches use `room/<room_id>/<agent_id>/<task_slug>` and integration branches use `integration/<room_id>/<task_slug>`;
- integration: the orchestrator owns the integration branch and integration tests. Final MR/merge still requires user or control approval;
- conflict resolution: facts and permissions are decided by manifest, evidence, Git, and tests; product tradeoffs go to the user; technical disagreements are recorded before the orchestrator decides;
- commit scope: a writing agent may commit only files allowed by its task packet. Extra files may be returned only as a patch proposal;
- failed tests: a task with failing required tests is `blocked`, with failure log, attempted fixes, and next-step recommendation.
- clarification: `clarificationTarget` wins. Otherwise product decisions go to the user, permission/security/fact conflicts go to control, implementation questions go to the orchestrator, and domain questions go to the relevant domain lead.
- permission gaps: an agent must generate a permission request and may include a read-only patch proposal. It must not continue by guessing authority.

These rules apply only after the room packet assigns a writing task. They do not grant live dispatch authority by themselves.

## Room Lifecycle And Memory Policy

Long-running collaboration follows the user's approved C/C/C/C/C/C decisions:

- long-term room: stores members, history, and standing rules only. Real work must happen in a temporary run or task packet;
- active room limit: one agent may belong to only one active room at a time;
- room exit: leaving a room requires an exit packet that says whether the normal thread resumes, archives, or becomes a detached handoff;
- memory access: room members get permission-scoped memory. Ordinary members read summaries; orchestrator/control can read full source chains; sensitive memory must be filtered;
- history display: default is the complete room flow with filters for direct, cc, broadcast, approval, evidence, task, and system messages;
- archived room restore: restoring an archived room requires a restore packet with reason, history scope, and current target;
- rule changes: members may propose changes, but only user/control approval can mutate the registry or contract.
- close authority: only the user can finally close a room. The orchestrator may submit a close request with final verdict, completed/open items, test/evidence summary, remaining risks, and handoff/archive path.

Chat memory, UI state, and unreviewed summaries are not authority. Memory must cite its source or be treated as a lead, not a fact.
