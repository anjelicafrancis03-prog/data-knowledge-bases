# Security Boundary

## Authority Model

This workbench is an operator console. It can summarize state and execute bounded local actions, but it does not grant authority to external agents or providers.

Authority remains with the Harness gate path and explicit human approvals.

The current controller is scoped to a local, single-operator loopback workbench. Its session cookie, Origin checks, Referer checks, and `X-Requested-With` header protect primarily against browser CSRF and accidental cross-origin web access. They are not a hard security boundary against another local process that can call `127.0.0.1` directly and spoof HTTP headers.

## Protected Zones

The workbench must not mutate:

- Credentials or secret stores.
- Browser profiles, cookies, localStorage, or login state.
- Codex config.
- MCP registration.
- Startup tasks.
- jcode normal profile.
- External publishing, merge, push, deployment, or payment surfaces.

## Route Classes

Read-only routes:

- `GET /api/status`
- `GET /api/gates`
- `GET /api/tasks`
- `GET /api/adapters`
- `GET /api/session`

Public `GET /api/status` and `GET /api/gates` return sanitized summaries. Full local file paths, local task queues, adapter registry details, and packet contents are reserved for same-origin workbench requests with the session cookie and workbench request header.

Mutating routes:

- `POST /api/tasks/create`
- `POST /api/task/<id>/state`
- `POST /api/open/<url|path>/<name>`
- `POST /api/action/<name>`
- `POST /api/adapter/<id>/dry-run`

Mutating routes require:

- HttpOnly same-origin workbench session cookie
- workbench request header
- allowed Origin when `strictOrigin` is true
- fixed controller-side allowlists

`GET /api/session` refreshes the HttpOnly session cookie but does not return the operator token in JSON.

Task packet reads must keep `packetPath` inside the local task-packet root before reading file content.

## Feature Flags

Committed defaults should keep high-risk groups off:

- `openTargets=false`
- `processActions=false`
- `dockerActions=false`

Local operators may enable these in ignored `config.local.json`.

## Current Gate Decisions

- O-review dispatch draft may remain schema-valid but not sent.
- jcode planning adapter remains non-canonical.
- Any real provider/O/jcode/deploy action requires a separate packet and exact approval phrase.
