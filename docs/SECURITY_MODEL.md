# Security Model

Aegix OS treats agents as principals, not scripts. An agent receives only scoped, temporary, revocable authority.

## Core Rule

Agents may prepare dangerous actions. Agents may not silently perform dangerous actions.

Dangerous actions include:

- external writes such as email, CRM updates, Git pushes, DNS changes, and public posts
- system changes such as packages, services, firewall, NGINX, users, and auth
- authority changes such as secrets, token scopes, exposed ports, and money movement
- device and sensor access such as camera, microphone, clipboard, USB, and radio

## Capability Checks

The broker should answer four questions before every meaningful action:

1. Who is asking?
2. What are they trying to do?
3. What authority do they currently have?
4. What evidence will prove the action succeeded or failed?

## Risk Levels

| Level | Name | Examples | Default |
|---|---|---|---|
| L0 | Observe | Scoped reads, search, summaries | Allowed if scoped |
| L1 | Draft | Scratch files and proposed diffs | Allowed in workspace |
| L2 | Local modify | Project patches and tests | Allowed by project policy |
| L3 | System modify | Packages, services, firewall | Approval required |
| L4 | External write | Email, CRM, Git push, web posts | Approval required |
| L5 | Authority change | Secrets, auth, users, exposed ports | Narrow approval token required |
| L6 | Device/sensor | Mic, camera, clipboard, USB | Visible grant required |

## Secrets

Agents should not receive raw long-lived secrets. They should receive short-lived, scoped ability through a broker:

- signed request ability
- short-lived token
- scoped proxy
- one-shot credential
- redacted handle

Every secret use should be recorded with agent, session, capability, destination, and result.

The preview operator surface is `secretsctl`:

- `secretsctl status --json`
- `secretsctl handles --json`
- `secretsctl policy --json`

These commands must return metadata and handles only. They must not print raw secret values.

## Memory

Primary memory must be inspectable files: Markdown, YAML, JSONL, SQLite, and Git-tracked project notes. Vector indexes may exist, but only as indexes over canonical files.

If the operator cannot grep it, diff it, back it up, and delete it, it is not primary memory.
