# Security Policy

This project is experimental and should not be used to grant production agents broad access.

## Reporting

Open a private advisory if available, or contact the maintainer directly before publishing exploit details.

## Non-negotiable security direction

- no ambient root for agents
- no raw long-lived secrets in agent environments
- no silent external side effects
- no unreviewed skill installation in privileged contexts
- no hidden primary memory store
