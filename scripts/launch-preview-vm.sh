#!/usr/bin/env bash
set -euo pipefail

nix run .#aegix-vm
exec ./result/bin/run-aegix-preview-vm
