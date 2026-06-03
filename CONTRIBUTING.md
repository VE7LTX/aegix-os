# Contributing

Aegix OS is pre-MVP. Contributions should preserve the core safety model.

## Rules

- Do not add broad root-level agent authority.
- Do not add raw secret exposure to agents.
- Do not add external write actions without approval-gate design.
- Every agent action feature must define a receipt format.
- Every risky action must define verification and rollback behavior.

## Preferred contribution types

- policy examples
- threat models
- NixOS modules
- rootless runtime profiles
- OpenClaw skill wrappers
- receipt schema improvements
- documentation
