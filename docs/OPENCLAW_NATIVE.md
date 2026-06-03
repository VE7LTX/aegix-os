# OpenClaw Native Integration

OpenClaw should run as a managed suite component inside Aegix OS boundaries. It should not be the root architecture and should not receive broad host authority.

## Integration Goals

- install OpenClaw through a declared profile
- run OpenClaw under an agent identity such as `openclaw-agent`
- mount OpenClaw skills as scoped workspaces
- mediate tool calls through the capability broker
- store per-skill receipts
- isolate browser, plugin, gateway, exec, and secret access
- snapshot OpenClaw state before upgrades or skill changes

## Non-Goals

- no wholesale vendoring without license and security review
- no privileged OpenClaw daemon as the trust root
- no ambient host filesystem access
- no raw secret injection into OpenClaw environments
- no unreviewed skill installation in privileged contexts

## First Profile

The first native profile should be read-mostly:

- scoped workspace
- no inbound ports
- GitHub egress only when required
- no LAN scan
- no raw shell outside sandbox
- no external write without approval token
