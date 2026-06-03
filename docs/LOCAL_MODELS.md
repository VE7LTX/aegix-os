# Local Model Services

Aegix OS should include local model services as part of the primary AI-first kit. The first target is Ollama because it provides a simple local API, model registry behavior, and broad model support.

## Ollama profile

Default posture:

- enabled through `services.aegix.ollama.enable`
- bound to `127.0.0.1`
- default port `11434`
- firewall closed by default
- model state target `/aegix/models/ollama`
- command surfaces through `agentctl models` and `agentctl ollama`

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
