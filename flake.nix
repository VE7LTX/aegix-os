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

        packages.secretsctl = pkgs.writeShellApplication {
          name = "secretsctl";
          runtimeInputs = [ python ];
          text = ''
            exec ${python}/bin/python ${self}/tools/secretsctl/secretsctl.py "$@"
          '';
        };

        packages.aegixtui = pkgs.writeShellApplication {
          name = "aegixtui";
          runtimeInputs = [ python pkgs.ncurses ];
          text = ''
            exec ${python}/bin/python ${self}/tools/aegixtui/aegixtui.py "$@"
          '';
        };

        packages.aegixai = pkgs.writeShellApplication {
          name = "aegixai";
          runtimeInputs = [ python ];
          text = ''
            exec ${python}/bin/python ${self}/tools/aegixai/aegixai.py "$@"
          '';
        };

        packages."aegix-query" = pkgs.writeShellApplication {
          name = "aegix-query";
          runtimeInputs = [ python ];
          text = ''
            exec ${python}/bin/python ${self}/tools/aegixquery/aegixquery.py "$@"
          '';
        };

        packages.codexcli = pkgs.writeShellApplication {
          name = "codexcli";
          runtimeInputs = [ pkgs.nodejs pkgs.git ];
          text = ''
            export NPM_CONFIG_CACHE="''${NPM_CONFIG_CACHE:-''${XDG_CACHE_HOME:-$HOME/.cache}/aegix/npm}"
            export NPM_CONFIG_AUDIT=false
            export NPM_CONFIG_FUND=false
            export NPM_CONFIG_UPDATE_NOTIFIER=false
            export NO_UPDATE_NOTIFIER=1
            export npm_config_cache="$NPM_CONFIG_CACHE"
            exec npm exec --yes --package @openai/codex@0.136.0 -- codex "$@"
          '';
        };

        packages.codex = pkgs.writeShellApplication {
          name = "codex";
          runtimeInputs = [ self.packages.${system}.codexcli ];
          text = ''
            exec codexcli "$@"
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

        packages.aegix-vm-gpu = pkgs.writeShellApplication {
          name = "aegix-vm-gpu";
          runtimeInputs = [ pkgs.nix ];
          text = ''
            echo "Building Aegix preview VM (GPU profile)..."
            nix build --no-write-lock-file ${self}#nixosConfigurations.aegix-preview-gpu.config.system.build.vm -L
            echo
            echo "Preview GPU VM built."
            echo "Run it with: ./result/bin/run-aegix-preview-vm"
          '';
        };

        packages.default = self.packages.${system}.agentctl;

        checks.agentctl-integration = pkgs.runCommand "aegix-agentctl-integration" {
          nativeBuildInputs = [ python ];
        } ''
          cp -r ${self} source
          chmod -R u+w source
          cd source
          ${python}/bin/python -m py_compile \
            tools/agentctl/agentctl.py \
            tools/aegixtui/aegixtui.py \
            tools/aegixai/aegixai.py \
            tools/aegixquery/aegixquery.py \
            tools/obsidianctl/obsidianctl.py \
            tools/secretsctl/secretsctl.py
          ${python}/bin/python tests/test_agentctl_integration.py
          ${python}/bin/python tests/test_aegixquery_integration.py
          touch $out
        '';
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
      nixosConfigurations.aegix-preview-gpu = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        specialArgs = { inherit self; };
        modules = [
          ./nixos/modules/aegix.nix
          ./nixos/hosts/aegix-preview/configuration.nix
          ./nixos/hosts/aegix-preview-gpu.nix
        ];
      };
    };
}

