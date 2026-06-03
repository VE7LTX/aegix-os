# Security Policy

This project is experimental and should not be used to grant production agents broad access.

## Reporting

Open a private advisory if available, or contact the maintainer before publishing exploit details.

Maintainer contact: VE7LTX on GitHub.

## Supported versions

This project is pre-MVP. Only the `main` branch is in scope for security reports.

## Security review priorities

Reports are especially useful when they identify ways for an agent, tool, integration, or policy gap to bypass:

- capability scoping
- approval tokens
- receipt generation
- rollback controls
- secret mediation
- egress restrictions

## Non-negotiable security direction

- no ambient root for agents
- no raw long-lived secrets in agent environments
- no silent external side effects
- no unreviewed skill installation in privileged contexts
- no hidden primary memory store
