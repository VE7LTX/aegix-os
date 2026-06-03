{
  description = "Aegix OS: capability-secured Linux agent appliance scaffold";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            git
            jq
            yq
            ripgrep
            fd
            podman
            python312
            python312Packages.typer
            python312Packages.pydantic
          ];
        };

        packages.agentctl = pkgs.writeShellApplication {
          name = "agentctl";
          runtimeInputs = [ pkgs.jq pkgs.ripgrep ];
          text = ''
            echo "Aegix agentctl scaffold"
            echo "Commands planned: agents, caps, run, diff, approve, rollback, receipts"
          '';
        };

        packages.default = self.packages.${system}.agentctl;
      }
    ) // {
      nixosModules.aegix = import ./nixos/modules/aegix.nix;
    };
}
