# Local Model Services

Aegix OS should include local model services as part of the primary AI-first kit. The first target is Ollama because it provides a simple local API, model registry behavior, and broad model support.

## Ollama profile

Default posture:

- enabled through `services.aegix.ollama.enable`
- bound to `127.0.0.1`
- default port `11434`
- default starter model `qwen3.5:0.8b`
- fallback model `tinyllama`
- firewall closed by default
- model state target `/aegix/models/ollama`
- command surfaces through `aegixai`, `agentctl models`, and `agentctl ollama`

NixOS module example:

```nix
{
  services.aegix = {
    enable = true;
    ollama.enable = true;
  };
}
```

LAN exposure should require explicit configuration:

```nix
{
  services.aegix.ollama = {
    enable = true;
    host = "0.0.0.0";
    openFirewall = true;
  };
}
```

## Native terminal copilot

`aegixai` is the Aegix-native terminal copilot. It talks to local Ollama over localhost and gives agents/operators a small local chat and command-suggestion surface.

The shell shortcut `? question` sends shell context into that same local path and records the chat as Markdown memory under `/aegix/notes/obsidian/90-terminal-chat/`.

Preview commands:

```bash
aegixai status --json
aegixai diagnose --json
aegixai warmup
aegixai models --json
aegixai ask "what should I inspect first?"
aegixai command "show failed services"
aegixai grow --json
```

The preview VM attempts to pull `tinyllama` and `qwen3.5:0.8b` through `aegix-ollama-model-pull.service`. If the VM is offline, boot continues and `aegixai status --json` reports the degraded model state.

On the preview VM, the first local inference can be slow because QEMU may fall back to software emulation. Use:

```bash
aegixai diagnose --json
aegixai warmup --timeout 900
aegixai ask "what should I inspect first?" --timeout 900
```

Non-JSON `ask`, `command`, and `warmup` show a wait indicator while the model loads.

`aegixai command` suggests commands only. It does not execute them. Future command execution should go through `agentctl` sessions, capability checks, receipts, and approvals.

## Growth model

The onboard local model should grow by proposing improvements, not by silently mutating the system.

Allowed in preview:

- write growth proposals under `/aegix/models/growth`
- suggest runbooks, command helpers, model changes, or policy changes
- summarize receipts and repeated operator workflows

Not allowed without approval:

- installing packages
- pulling larger models
- restarting services
- changing authentication
- exposing Ollama to the LAN
- writing to external systems

## Agent rules

- Prefer local models for private, credential-adjacent, or system-specific data.
- Do not expose Ollama to the LAN by default.
- Record model name, prompt class, data class, and result status in receipts.
- Treat model downloads as package-like changes when they consume bandwidth, disk, or paid resources.
- Keep model inventory inspectable through files and `agentctl`.

## Future adapters

- llama.cpp server
- vLLM server
- Transformers.js local browser/WebGPU profile
- model router with local/cloud policy
- per-agent model allowlists
