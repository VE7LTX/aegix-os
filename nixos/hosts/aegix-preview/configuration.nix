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
      agentctl caps --json
      agentctl index --json
      agentctl search-index Aegix --json
      agentctl graph --json
      agentctl run demo-agent --task "Create preview receipt" --workspace /aegix/scratch/demo --json
      agentctl receipts --json
      aegixai status --json
      aegixai diagnose --json
      aegixai warmup
      aegixai ask "what should I inspect first?"
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
      printf 'Use "? question" to send shell context to local AI.\n'
      if [ -r /aegix/logs/startup-summary.md ]; then
        printf '\n'
        printf 'Setup log:\n'
        ${pkgs.coreutils}/bin/cat /aegix/logs/startup-summary.md
        printf '\n'
      fi
      if [ -z "$AEGIX_NO_TUI" ] && command -v aegixtui >/dev/null 2>&1; then
        printf 'Press Space to continue to the operator TUI. Press q to return to shell later.\n'
        printf '\n'
        while :; do
          if IFS= read -r -n 1 key; then
            if [ "$key" = " " ]; then
              break
            fi
          else
            break
          fi
        done
        printf '\n'
        aegixtui
      fi
    fi

    _aegix_query() {
      local root="''${AEGIX_ROOT:-/aegix}"
      local tail_file="$root/logs/terminal-tail.md"
      local tail_dir
      local history_tail
      tail_dir="$(${pkgs.coreutils}/bin/dirname "$tail_file")"
      history_tail="$(history 20 2>/dev/null | ${pkgs.gnused}/bin/sed -E 's/([Pp]assword|[Tt]oken|[Ss]ecret|[Kk]ey|[Aa]uth|[Cc]redential|[Pp]assphrase)=([^[:space:]]+)/\1=[REDACTED]/g; s/(ghp_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+|xox[pbar]-[A-Za-z0-9-]+|AKIA[0-9A-Z]{16})/[REDACTED]/g')"
      ${pkgs.coreutils}/bin/mkdir -p "$tail_dir"
      ${pkgs.coreutils}/bin/cat > "$tail_file" <<EOF
# Aegix Terminal Tail

- captured_at: $(${pkgs.coreutils}/bin/date -u +%Y-%m-%dT%H:%M:%SZ)
- cwd: $PWD
- user: $USER

\`\`\`text
$history_tail
\`\`\`
EOF
      if [ "$#" -gt 0 ]; then
        printf '\n## Query\n\n' >> "$tail_file"
        printf '%s\n' "$*" >> "$tail_file"
      fi
      aegix-query "$@"
    }
  '';

  environment.systemPackages = with pkgs; [
    self.packages.${pkgs.system}.agentctl
    self.packages.${pkgs.system}.aegixai
    self.packages.${pkgs.system}.aegixtui
    self.packages.${pkgs.system}."aegix-query"
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
  environment.variables.AEGIX_ROOT = "/aegix";
  environment.variables.AEGIX_AI_MODEL = "qwen3.5:0.8b";
  environment.variables.AEGIX_AI_FALLBACK_MODEL = "tinyllama";
  environment.variables.OLLAMA_HOST = "http://127.0.0.1:11434";
  environment.shellAliases = {
    aegix-status = "agentctl status --json";
    aegix-doctor = "agentctl doctor --json";
    aegix-verify = "agentctl verify --json";
    aegix-paths = "agentctl paths --json";
    aegix-index = "agentctl index --json";
    aegix-search = "agentctl search-index";
    aegix-graph = "agentctl graph --json";
    aegix-demo = "agentctl run demo-agent --task 'Create preview receipt' --workspace /aegix/scratch/demo --json";
    aegix-receipts = "agentctl receipts --json";
    aegix-events = "agentctl events --json";
    aegix-ai = "aegixai";
    aegix-ai-diagnose = "aegixai diagnose --json";
    aegix-ai-warmup = "aegixai warmup";
    aegix-ask = "aegixai ask";
    "?" = "_aegix_query";
    aegix-command = "aegixai command";
    aegix-models = "aegixai models --json";
    aegix-failed = "systemctl --failed --no-pager --plain";
  };

  services.aegix = {
    enable = true;
    package = self.packages.${pkgs.system}.agentctl;
    ollama.enable = true;
    data.enable = true;
  };

  virtualisation.vmVariant = {
    virtualisation = {
      memorySize = 8192;
      cores = 4;
      diskSize = 16384;
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
      ${pkgs.coreutils}/bin/chmod 0770 /aegix/scratch /aegix/projects /aegix/sessions /aegix/receipts /aegix/approvals /aegix/snapshots /aegix/checkpoints /aegix/index /aegix/logs /aegix/logs/verify /aegix/runbooks /aegix/notes/obsidian /aegix/notes/obsidian/90-terminal-chat
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
      ${pkgs.coreutils}/bin/cat > /aegix/policy/capabilities.yaml <<'EOF'
mode: preview-friendly
allowed_without_approval:
  - files.read
  - status.read
  - logs.read
  - agent.session.create
  - receipt.write
local_write_roots:
  - /aegix/scratch
  - /aegix/projects
approval_required:
  - external.write
  - secret.read
  - service.restart
  - package.install
  - auth.change
  - system.modify
denied_by_default:
  - money.movement
  - device.sensor
  - network.lan_scan
EOF
      ${pkgs.coreutils}/bin/cat > /aegix/policy/rollback.yaml <<'EOF'
mode: preview-metadata-only
default_behavior:
  - create receipt before reporting completion
  - create checkpoint metadata before rollback
  - show restore plan before modifying files
  - require approval token before destructive rollback
deferred_backends:
  - btrfs snapshots
  - zfs snapshots
  - nix generation rollback
  - declarative config patch reversal
EOF
      ${pkgs.coreutils}/bin/cat > /aegix/runbooks/first-agent.md <<'EOF'
# First Agent Runbook

Start here after boot:

```bash
agentctl doctor --json
agentctl paths --json
agentctl caps --json
agentctl index --json
agentctl search-index Aegix --json
agentctl graph --json
agentctl run demo-agent --task "Create preview receipt" --workspace /aegix/scratch/demo --json
agentctl receipts --json
agentctl events --json
aegixai status --json
aegixai diagnose --json
aegixai warmup
aegixai ask "what should I inspect first?"
```

Rules:

- Use `/aegix/scratch` for experiments.
- Use `/aegix/projects` for project work.
- Leave a receipt for every meaningful write.
- Run `agentctl index --json` after adding many files.
- Use `agentctl search-index "query" --json` before expensive recursive scans.
- Treat `/aegix/index/vector-registry.json` as the vector DB attachment point, not the source of truth.
- Use `agentctl snapshot <session_id> --json` before rollback planning.
- Use `agentctl rollback <session_id> --json` to show the non-destructive rollback plan.
- Dangerous actions stay approval-only.
- Use `aegixai ask "question"` for local model help.
- Use `aegixai command "task"` for command suggestions. It does not execute them.
EOF
      ${pkgs.coreutils}/bin/cat > /aegix/runbooks/command-guide.md <<'EOF'
# Aegix Command Guide

Start with:

```bash
agentctl doctor --json
agentctl paths --json
agentctl caps --json
agentctl commands --json
agentctl help run --json
```

Look for `agent_help` in JSON output. It explains intent, safe usage, expected fields, and next steps.

Session evidence flow:

```bash
agentctl run demo-agent --task "Create preview receipt" --workspace /aegix/scratch/demo --json
agentctl receipts --json
agentctl inspect <session_id> --json
agentctl snapshot <session_id> --json
agentctl rollback <session_id> --json
```
EOF
      ${pkgs.coreutils}/bin/cat > /aegix/runbooks/local-ai.md <<'EOF'
# Local Aegix AI

`aegixai` is the native terminal copilot for the preview VM.

Default model:

```text
qwen3.5:0.8b
```

Commands:

```bash
aegixai status --json
aegixai diagnose --json
aegixai warmup
aegixai models --json
aegixai ask "what should I inspect first?"
aegixai command "show failed services"
aegixai grow --json
```

Rules:

- `aegixai` talks to Ollama on localhost.
- The first answer may take several minutes under QEMU software emulation.
- Run `aegixai diagnose --json` if the local model appears stalled.
- Run `aegixai warmup --timeout 900` before the first real chat if needed.
- It suggests commands; it does not execute them.
- It may propose upgrades in `/aegix/models/growth`.
- It may not silently upgrade itself, restart services, install packages, or change auth.
EOF
      ${pkgs.coreutils}/bin/cat > /aegix/runbooks/file-index-graph.md <<'EOF'
# File Index And Graph

Use the local index before expensive recursive scans:

```bash
agentctl index --json
agentctl search-index "query" --json
agentctl graph --json
```

Artifacts:

```text
/aegix/index/files.jsonl
/aegix/index/graph.json
/aegix/index/aegix_index.sqlite
/aegix/index/vector-registry.json
```

Vector DB policy:

- canonical truth stays in files and SQLite/JSON graph records
- vector storage is only a secondary index
- do not embed secret stores or credential-adjacent files without explicit policy
EOF
      ${pkgs.coreutils}/bin/cat > /aegix/notes/obsidian/00-inbox/aegix-preview.md <<'EOF'
# Aegix Preview

This VM previews the Aegix OS AI-first operator layout.

Try:

```bash
aegixtui
agentctl status --json
agentctl doctor --json
agentctl paths --json
agentctl commands --json
agentctl caps --json
agentctl index --json
agentctl search-index Aegix --json
agentctl graph --json
agentctl run demo-agent --task "Create preview receipt" --workspace /aegix/scratch/demo --json
agentctl receipts --json
agentctl events --json
aegixai status --json
aegixai diagnose --json
aegixai warmup
aegixai ask "what should I inspect first?"
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

  systemd.services.aegix-startup-log = {
    description = "Write Aegix startup summary";
    wantedBy = [ "multi-user.target" ];
    after = [ "aegix-preview-note.service" "aegix-ollama-model-pull.service" "systemd-tmpfiles-setup.service" ];
    serviceConfig = {
      Type = "oneshot";
      User = "operator";
      Group = "aegix";
    };
    script = ''
      set +e
      ${pkgs.coreutils}/bin/mkdir -p /aegix/logs
      tmp="$(${pkgs.coreutils}/bin/mktemp /aegix/logs/startup-summary.XXXXXX)"
      {
        printf '# Aegix Startup Summary\n\n'
        printf '- generated_at: %s\n' "$(${pkgs.coreutils}/bin/date -u +%Y-%m-%dT%H:%M:%SZ)"
        printf '- host: %s\n' "$(${pkgs.coreutils}/bin/hostname 2>/dev/null || echo unknown)"
        printf '\n## Setup Log\n\n'
        if [ -r /aegix/logs/ollama-model-pull.log ]; then
          printf '```text\n'
          ${pkgs.coreutils}/bin/tail -n 200 /aegix/logs/ollama-model-pull.log
          printf '\n```\n'
        else
          printf '_No Ollama model-pull log found._\n'
        fi
        printf '\n## Index Refresh\n\n'
        if [ -r /aegix/logs/index-refresh.json ]; then
          printf '```json\n'
          ${pkgs.coreutils}/bin/cat /aegix/logs/index-refresh.json
          printf '\n```\n'
        else
          printf '_No index refresh artifact found yet._\n'
        fi
        printf '\n## Failed Services\n\n'
        printf '```text\n'
        ${pkgs.systemd}/bin/systemctl --failed --no-pager --plain 2>&1 || true
        printf '\n```\n'
      } > "$tmp"
      ${pkgs.coreutils}/bin/mv "$tmp" /aegix/logs/startup-summary.md
      ${pkgs.coreutils}/bin/chmod 0644 /aegix/logs/startup-summary.md
      exit 0
    '';
  };

  systemd.services.aegix-ollama-model-pull = {
    description = "Pull Aegix default local Ollama model";
    wantedBy = [ "multi-user.target" ];
    after = [ "ollama.service" "network-online.target" "aegix-preview-note.service" ];
    wants = [ "network-online.target" ];
    serviceConfig = {
      Type = "oneshot";
      User = "operator";
      Group = "aegix";
      TimeoutStartSec = "20min";
    };
    script = ''
      set +e
      ${pkgs.coreutils}/bin/mkdir -p /aegix/models/growth /aegix/logs
      ${pkgs.coreutils}/bin/date --iso-8601=seconds > /aegix/logs/ollama-model-pull.log
      for model in tinyllama qwen3.5:0.8b; do
        echo "pulling $model" >> /aegix/logs/ollama-model-pull.log
        ${pkgs.ollama}/bin/ollama pull "$model" >> /aegix/logs/ollama-model-pull.log 2>&1 || true
      done
      echo "model pull attempted for fallback and primary models; aegixai will report degraded status if offline" >> /aegix/logs/ollama-model-pull.log
      exit 0
    '';
  };

  systemd.services.aegix-index-refresh = {
    description = "Refresh Aegix file graph and text index";
    wantedBy = [ "multi-user.target" ];
    after = [ "aegix-preview-note.service" "systemd-tmpfiles-setup.service" ];
    serviceConfig = {
      Type = "oneshot";
      User = "aegix";
      Group = "aegix";
    };
    script = ''
      ${self.packages.${pkgs.system}.agentctl}/bin/agentctl --root /aegix index --max-files 5000 --json > /aegix/logs/index-refresh.json
    '';
  };

  systemd.timers.aegix-index-refresh = {
    description = "Periodic Aegix file index refresh";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "2min";
      OnUnitActiveSec = "30min";
      Unit = "aegix-index-refresh.service";
    };
  };
}
