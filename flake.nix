{
  description = "Aegix OS: AI-first Linux workstation/server scaffold";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachSystem [ "x86_64-linux" "aarch64-linux" ] (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python312;
      in {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            git
            jq
            yq
            ripgrep
            fd
            bat
            eza
            fzf
            zoxide
            direnv
            tmux
            neovim
            helix
            lazygit
            btop
            ncdu
            glow
            just
            sd
            podman
            python312
            python312Packages.typer
            python312Packages.pydantic
          ];
        };

        packages.agentctl = pkgs.writeShellApplication {
          name = "agentctl";
          runtimeInputs = [ python pkgs.jq pkgs.ripgrep ];
          text = ''
            exec ${python}/bin/python ${self}/tools/agentctl/agentctl.py "$@"
          '';
        };

        packages.obsidianctl = pkgs.writeShellApplication {
          name = "obsidianctl";
          runtimeInputs = [ python pkgs.ripgrep ];
          text = ''
            exec ${python}/bin/python ${self}/tools/obsidianctl/obsidianctl.py "$@"
          '';
        };

        packages.aegix-vm = pkgs.writeShellApplication {
          name = "aegix-vm";
          text = ''
            echo "Aegix VM scaffold"
            echo "The NixOS VM profile is not implemented yet."
            echo "Next target: add nixosConfigurations.aegix-vm and a runnable VM app."
          '';
        };

        packages.default = self.packages.${system}.agentctl;
      }
    ) // {
      nixosModules.aegix = import ./nixos/modules/aegix.nix;
    };
}
