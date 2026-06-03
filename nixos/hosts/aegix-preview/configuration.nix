{ self, pkgs, ... }:

{
  system.stateVersion = "25.05";

  imports = [ ];

  networking.hostName = "aegix-preview";
  networking.firewall.enable = true;

  time.timeZone = "America/Vancouver";

  boot.consoleLogLevel = 3;
  boot.loader.grub.devices = [ "nodev" ];
  boot.kernelParams = [
    "quiet"
    "loglevel=3"
    "rd.systemd.show_status=auto"
    "systemd.show_status=auto"
    "udev.log_level=3"
  ];

  fileSystems."/" = {
    device = "/dev/disk/by-label/nixos";
    fsType = "ext4";
  };

  users.users.operator = {
    isNormalUser = true;
    description = "Aegix preview operator";
    extraGroups = [ "aegix" "wheel" ];
    initialPassword = "aegix";
  };

  security.sudo.wheelNeedsPassword = false;
  services.getty.autologinUser = "operator";
  services.getty.helpLine = ''
    Aegix OS preview console
    AI-first appliance profile on a reproducible NixOS base.
  '';

  environment.etc."issue".text = ''
    Aegix OS Preview (\m) - \l

    Agent-first Linux appliance console
    Login: operator / password: aegix

  '';

  environment.etc."motd".text = ''
    Aegix OS Preview
    Agent-first Linux appliance profile

    Quick checks:
      aegixtui
      agentctl status --json
      secretsctl status --json
      codexcli --version
      obsidianctl path --json
      obsidianctl search Aegix --json
      systemctl status ollama

    Aegix root: /aegix
    Obsidian AI memory: /aegix/notes/obsidian
  '';

  environment.interactiveShellInit = ''
    if [ -n "$PS1" ] && [ "$USER" = "operator" ] && [ -z "$AEGIX_BANNER_SHOWN" ]; then
      export AEGIX_BANNER_SHOWN=1
      printf '\n'
      printf 'Aegix OS Preview\n'
      printf 'Agent-first Linux appliance console\n'
      printf 'Root: /aegix | Memory: /aegix/notes/obsidian | Models: Ollama localhost:11434\n'
      printf 'Opening operator TUI. Press q to return to shell. Run aegixtui anytime.\n'
      printf '\n'
      if [ -z "$AEGIX_NO_TUI" ] && command -v aegixtui >/dev/null 2>&1; then
        aegixtui
      fi
    fi
  '';

  environment.systemPackages = with pkgs; [
    self.packages.${pkgs.system}.agentctl
    self.packages.${pkgs.system}.aegixtui
    self.packages.${pkgs.system}.codex
    self.packages.${pkgs.system}.codexcli
    self.packages.${pkgs.system}.obsidianctl
    self.packages.${pkgs.system}.secretsctl
    bashInteractive
    bat
    btop
    duckdb
    eza
    fd
    fzf
    git
    glow
    helix
    jq
    just
    lazygit
    ncdu
    neovim
    ollama
    postgresql
    prometheus
    qdrant
    redis
    ripgrep
    sqlite
    tmux
    yq
    zoxide
  ];

  programs.command-not-found.enable = false;
  services.logrotate.enable = false;

  services.aegix = {
    enable = true;
    package = self.packages.${pkgs.system}.agentctl;
    ollama.enable = true;
    data.enable = true;
  };

  virtualisation.vmVariant = {
    virtualisation = {
      memorySize = 4096;
      cores = 2;
      diskSize = 8192;
      graphics = false;
    };
  };

  systemd.services.aegix-preview-note = {
    description = "Create Aegix preview welcome note";
    wantedBy = [ "multi-user.target" ];
    after = [ "systemd-tmpfiles-setup.service" ];
    serviceConfig = {
      Type = "oneshot";
      User = "aegix";
      Group = "aegix";
    };
    script = ''
      ${self.packages.${pkgs.system}.obsidianctl}/bin/obsidianctl init --vault /aegix/notes/obsidian
      ${pkgs.coreutils}/bin/cat > /aegix/secrets/handles.json <<'EOF'
[
  {
    "handle": "codex.operator.auth",
    "purpose": "Codex CLI operator authentication state",
    "raw_value_access": false,
    "status": "managed-by-tool-cache"
  },
  {
    "handle": "openclaw.operator.auth",
    "purpose": "OpenClaw operator authentication placeholder",
    "raw_value_access": false,
    "status": "planned"
  },
  {
    "handle": "hubspot.crm.proxy",
    "purpose": "Scoped CRM API proxy placeholder",
    "raw_value_access": false,
    "status": "planned"
  }
]
EOF
      ${pkgs.coreutils}/bin/cat > /aegix/notes/obsidian/00-inbox/aegix-preview.md <<'EOF'
# Aegix Preview

This VM previews the Aegix OS AI-first operator layout.

Try:

```bash
aegixtui
agentctl status --json
agentctl commands --json
secretsctl status --json
secretsctl handles --json
codexcli --version
obsidianctl path --json
obsidianctl search Aegix --json
systemctl status aegix-agentd
systemctl status ollama
ls -la /aegix
```
EOF
    '';
  };
}
