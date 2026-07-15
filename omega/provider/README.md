# OmegaCLI Provider

The **OmegaCLI Provider** is a custom model serving platform — like OpenCode Zen — that gives you:

- **5 free models** — DeepSeek V4 Flash, Mimo 2.5, Nemotron 3 Ultra, North Mini Code, Hybrid 3
- **API key management** — generate, validate, revoke keys programmatically
- **Rate limiting** — per-key sliding window rate limiter
- **OpenCode-compatible API** — drop-in replacement for OpenAI-style endpoints

## Quick Start

```python
from omega.provider import OmegaCLIProvider

provider = OmegaCLIProvider()

# List available models
for m in provider.list_models():
    print(f"{m['id']}: {m['context_length']} ctx")

# Generate an API key
key_info = provider.create_api_key("my-app")
print(f"Your key: {key_info['key']}")

# Chat completion
response = provider.chat(
    model="deepseek-v4-flash-free",
    messages=[{"role": "user", "content": "Hello!"}],
    api_key=key_info["key"],
)
```

## 5 Free Models

| Model ID | Context | Best For |
|---|---|---|
| `deepseek-v4-flash-free` | 16K | Fast everyday tasks |
| `mimo-v2.5-free` | 8K | General purpose |
| `nemotron-3-ultra-free` | 64K | Complex reasoning, long docs |
| `north-mini-code-free` | 16K | Code generation |
| `hy3-free` | 32K | Mixed workloads |

## API Key Management

```python
# Create
key = provider.create_api_key("dev-server")

# Validate
provider.key_store.validate(key["key"])  # True/False

# Revoke
provider.revoke_api_key(key["key"])

# List all
keys = provider.list_api_keys()
```

## Running as a Server

```bash
# Serve the OmegaCLI provider as a FastAPI endpoint
python -m omega.provider.server
```

This starts a REST API at `http://localhost:8080/v1` compatible with the OpenAI API format — any OpenAI client can use it by setting `base_url`.

## Architecture

```
┌──────────────┐     ┌────────────────┐     ┌─────────────┐
│  Any Client  │────▶│ OmegaCLI       │────▶│ OpenCode    │
│  (OpenAI SDK)│     │ Provider       │     │ Zen API     │
└──────────────┘     │ (auth, limits) │     └─────────────┘
                     └────────────────┘
                           │
                     ┌─────┴──────┐
                     │ API Key    │
                     │ Store      │
                     └────────────┘
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OMEGA_API_KEY` | `""` | Default API key for requests |
| `OMEGA_PROVIDER_URL` | `https://opencode.ai/zen/v1` | Upstream model API base URL |
| `OMEGA_RATE_LIMIT` | `60` | Max requests per minute per key |
