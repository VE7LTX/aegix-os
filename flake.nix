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
            sqlite
            postgresql
            duckdb
            redis
            qdrant
            prometheus
            ollama
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
          runtimeInputs = [ pkgs.nix ];
          text = ''
            echo "Building Aegix preview VM..."
            nix build --no-write-lock-file ${self}#nixosConfigurations.aegix-preview.config.system.build.vm -L
            echo
            echo "Preview VM built."
            echo "Run it with: ./result/bin/run-aegix-preview-vm"
          '';
        };

        packages.default = self.packages.${system}.agentctl;
      }
    ) // {
      nixosModules.aegix = import ./nixos/modules/aegix.nix;
      nixosConfigurations.aegix-preview = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        specialArgs = { inherit self; };
        modules = [
          ./nixos/modules/aegix.nix
          ./nixos/hosts/aegix-preview/configuration.nix
        ];
      };
    };
}
