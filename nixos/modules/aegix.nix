{ config, lib, pkgs, ... }:

let
  cfg = config.services.aegix;
in
{
  options.services.aegix = {
    enable = lib.mkEnableOption "Aegix OS agent appliance scaffold";

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
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ];

    users.groups.aegix = { };
    users.users.aegix = {
      isSystemUser = true;
      group = "aegix";
      home = cfg.root;
      createHome = true;
      description = "Aegix agent appliance service account";
    };

    systemd.tmpfiles.rules = [
      "d ${cfg.root} 0750 aegix aegix - -"
      "d ${cfg.root}/agents 0750 aegix aegix - -"
      "d ${cfg.root}/memory 0750 aegix aegix - -"
      "d ${cfg.root}/policy 0750 aegix aegix - -"
      "d ${cfg.root}/projects 0750 aegix aegix - -"
      "d ${cfg.root}/receipts 0750 aegix aegix - -"
      "d ${cfg.root}/snapshots 0750 aegix aegix - -"
      "d ${cfg.root}/logs 0750 aegix aegix - -"
    ];

    systemd.services.aegix-agentd = {
      description = "Aegix agent session runner scaffold";
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
  };
}
