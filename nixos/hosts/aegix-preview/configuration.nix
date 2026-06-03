{ self, pkgs, ... }:

{
  system.stateVersion = "25.05";

  imports = [ ];

  networking.hostName = "aegix-preview";
  networking.firewall.enable = true;

  time.timeZone = "America/Vancouver";

  users.users.operator = {
    isNormalUser = true;
    description = "Aegix preview operator";
    extraGroups = [ "aegix" "wheel" ];
    initialPassword = "aegix";
  };

  security.sudo.wheelNeedsPassword = false;
  services.getty.autologinUser = "operator";

  environment.systemPackages = with pkgs; [
    self.packages.${pkgs.system}.agentctl
    self.packages.${pkgs.system}.obsidianctl
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
      ${pkgs.coreutils}/bin/cat > /aegix/notes/obsidian/00-inbox/aegix-preview.md <<'EOF'
# Aegix Preview

This VM previews the Aegix OS AI-first operator layout.

Try:

```bash
agentctl status --json
agentctl commands --json
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
