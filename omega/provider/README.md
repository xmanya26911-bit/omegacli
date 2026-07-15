# Omega Custom Provider

This directory contains the infrastructure to run your **own AI model provider** — similar to how OpenCode Zen provides free models through their API.

## How It Works

Instead of relying on third-party API endpoints, you can:

1. **Self-host models** — Run open-weight models (DeepSeek, Llama, Qwen, etc.) via [vLLM](https://github.com/vllm-project/vllm), [ollama](https://ollama.ai), or any OpenAI-compatible server
2. **Proxy existing providers** — Route through your own API gateway for rate limiting, auth, and logging
3. **Offer your own API keys** — Generate and manage keys for users

## Getting Started

### 1. Set Up a Model Server

```bash
# Using vLLM (recommended for production)
pip install vllm
vllm serve deepseek-ai/DeepSeek-R1-Distill-Qwen-7B --api-key your-key-here

# Using ollama (simpler for testing)
ollama pull llama3.2
ollama serve
```

### 2. Configure Omega

Set environment variables:

```bash
export OMEGA_PROVIDER_URL="http://localhost:8000/v1"
export OMEGA_PROVIDER_KEY="your-custom-api-key"
export OMEGA_USE_CUSTOM_PROVIDER=1
```

Or add to `~/.omega/config.json`:

```json
{
  "provider": "custom",
  "base_url": "http://localhost:8000/v1",
  "api_key": "your-custom-api-key"
}
```

### 3. Add Models

Edit `omega/provider/__init__.py` to add your models to `PROVIDER_CONFIG` or `DEFAULT_MODELS`.

## API Key Generation

For production, set up a simple API key service:

```python
from omega.provider import generate_key, validate_api_key

# Generate a new key
key = generate_key("user@example.com")
# => "omg_xxxx..."

# Validate on each request
if validate_api_key(request_api_key):
    # serve model
    pass
```

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌────────────────┐
│   Omega CLI     │────▶│ Custom Proxy │────▶│  Model Server  │
│ (python main.py)│     │ (this module)│     │ (vLLM/ollama)  │
└─────────────────┘     └──────────────┘     └────────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │  Rate Limiter│
                        │  Auth Check  │
                        │  Logging     │
                        └──────────────┘
```

## Future

- Admin dashboard for key management
- Usage analytics
- Model routing (free vs premium tiers)
- Usage-based billing
