#!/usr/bin/env bash
set -euo pipefail

if command -v nix >/dev/null 2>&1; then
  nix --version
else
  if [ ! -d /nix ]; then
    sudo mkdir -m 0755 /nix
    sudo chown "$USER" /nix
  fi

  curl -L https://nixos.org/nix/install -o /tmp/install-nix.sh
  sh /tmp/install-nix.sh --no-daemon
fi

mkdir -p "$HOME/.config/nix"
if [ ! -f "$HOME/.config/nix/nix.conf" ] || ! grep -q "experimental-features" "$HOME/.config/nix/nix.conf"; then
  printf '%s\n' 'experimental-features = nix-command flakes' >> "$HOME/.config/nix/nix.conf"
fi

. "$HOME/.nix-profile/etc/profile.d/nix.sh"
nix --version
nix flake --version
