# Third-Party License Tracking

This file tracks expected upstream components and their licensing status. It is not a complete legal review.

## Core upstream components

| Component | Intended use | License note |
|---|---|---|
| Nix | package manager / build substrate | Nix upstream licensing applies |
| NixOS / nixpkgs | base system profile and modules | nixpkgs contains many packages with individual licenses |
| Podman | rootless container runtime | upstream license applies |
| OpenClaw | native managed agent suite component | upstream license applies; do not vendor without review |
| OPA | policy engine candidate | upstream license applies |
| Python | CLI and prototype daemons | upstream license applies |

## Project rule

Aegix-owned source code is Apache-2.0 unless a file states otherwise.

Third-party code should not be copied into this repository unless:

1. its license permits redistribution,
2. attribution is preserved,
3. the copied source is tracked in this file or a generated license manifest,
4. the reason for vendoring is documented.

## OpenClaw integration rule

OpenClaw should be integrated as an upstream dependency, container image, flake input, package, or install profile. It should not be copied wholesale into Aegix without a license and security review.
