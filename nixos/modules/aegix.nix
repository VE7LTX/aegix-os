{ config, lib, pkgs, ... }:

let
  cfg = config.services.aegix;
in
{
  options.services.aegix = {
    enable = lib.mkEnableOption "Aegix OS AI-first workstation/server scaffold";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.writeShellApplication {
        name = "agentctl";
        text = ''
          echo "Aegix agentctl scaffold"
        '';
      };
      description = "Package that provides the agentctl command.";
    };

    root = lib.mkOption {
      type = lib.types.str;
      default = "/aegix";
      description = "Root directory for Aegix agent state, receipts, policy, and logs.";
    };

    ollama = {
      enable = lib.mkEnableOption "Ollama local model service for Aegix agents";

      package = lib.mkOption {
        type = lib.types.package;
        default = pkgs.ollama;
        description = "Ollama package to install and run.";
      };

      host = lib.mkOption {
        type = lib.types.str;
        default = "127.0.0.1";
        description = "Address for the Ollama service to bind.";
      };

      port = lib.mkOption {
        type = lib.types.port;
        default = 11434;
        description = "Port for the Ollama service.";
      };

      openFirewall = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Whether to open the Ollama port in the host firewall.";
      };
    };

    data = {
      enable = lib.mkEnableOption "Aegix database, vector, and time-series tool suite";

      packages = lib.mkOption {
        type = lib.types.listOf lib.types.package;
        default = with pkgs; [
          sqlite
          postgresql
          duckdb
          redis
          qdrant
          prometheus
        ];
        description = "Database and data-service tools to expose in the Aegix profile.";
      };
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ]
      ++ lib.optionals cfg.ollama.enable [ cfg.ollama.package ]
      ++ lib.optionals cfg.data.enable cfg.data.packages;

    users.groups.aegix = { };
    users.users.aegix = {
      isSystemUser = true;
      group = "aegix";
      home = cfg.root;
      createHome = true;
      description = "Aegix AI-first system service account";
    };

    systemd.tmpfiles.rules = [
      "d ${cfg.root} 0750 aegix aegix - -"
      "d ${cfg.root}/agents 0750 aegix aegix - -"
      "d ${cfg.root}/commands 0750 aegix aegix - -"
      "d ${cfg.root}/memory 0750 aegix aegix - -"
      "d ${cfg.root}/models 0750 aegix aegix - -"
      "d ${cfg.root}/models/ollama 0750 aegix aegix - -"
      "d ${cfg.root}/data 0750 aegix aegix - -"
      "d ${cfg.root}/data/sqlite 0750 aegix aegix - -"
      "d ${cfg.root}/data/postgres 0750 aegix aegix - -"
      "d ${cfg.root}/data/vector 0750 aegix aegix - -"
      "d ${cfg.root}/data/timeseries 0750 aegix aegix - -"
      "d ${cfg.root}/data/cache 0750 aegix aegix - -"
      "d ${cfg.root}/data/warehouse 0750 aegix aegix - -"
      "d ${cfg.root}/notes 0750 aegix aegix - -"
      "d ${cfg.root}/notes/obsidian 0750 aegix aegix - -"
      "d ${cfg.root}/mcp 0750 aegix aegix - -"
      "d ${cfg.root}/api 0750 aegix aegix - -"
      "d ${cfg.root}/plugins 0750 aegix aegix - -"
      "d ${cfg.root}/policy 0750 aegix aegix - -"
      "d ${cfg.root}/projects 0750 aegix aegix - -"
      "d ${cfg.root}/receipts 0750 aegix aegix - -"
      "d ${cfg.root}/secrets 0750 aegix aegix - -"
      "d ${cfg.root}/appliances 0750 aegix aegix - -"
      "d ${cfg.root}/snapshots 0750 aegix aegix - -"
      "d ${cfg.root}/logs 0750 aegix aegix - -"
      "d ${cfg.root}/screenshots 0750 aegix aegix - -"
      "d ${cfg.root}/runbooks 0750 aegix aegix - -"
      "d ${cfg.root}/scratch 0750 aegix aegix - -"
    ];

    systemd.services.aegix-agentd = {
      description = "Aegix AI-first session runner scaffold";
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        Type = "oneshot";
        User = "aegix";
        Group = "aegix";
        StateDirectory = "aegix";
      };
      script = ''
        ${cfg.package}/bin/agentctl status
      '';
    };

    services.ollama = lib.mkIf cfg.ollama.enable {
      enable = true;
      package = cfg.ollama.package;
      host = cfg.ollama.host;
      port = cfg.ollama.port;
    };

    networking.firewall.allowedTCPPorts =
      lib.mkIf cfg.ollama.openFirewall [ cfg.ollama.port ];
  };
}
