#!/usr/bin/env bash
# Deploy Omega Provider API to Render (free tier)
# Usage: bash deploy.sh
set -euo pipefail

PROJECT="omega-provider"
REPO_DIR="/d/TERMINALCLI/omegacli-clean"

echo "==> Creating Render deploy config..."

cat > "$REPO_DIR/render.yaml" << 'EOF'
services:
  - type: web
    name: omega-provider
    runtime: python
    repo: https://github.com/xmanya26911-bit/omegacli
    branch: main
    buildCommand: pip install -e . fastapi uvicorn
    startCommand: python -m omega.provider.server
    envVars:
      - key: OMEGA_PROVIDER_PORT
        value: "10000"
      - key: OMEGA_PROVIDER_HOST
        value: "0.0.0.0"
EOF

echo "render.yaml created"
echo ""
echo "==> To deploy:"
echo "   1. Push to git: git add render.yaml && git commit -m 'Add Render config' && git push"
echo "   2. Go to https://dashboard.render.com/select-repo"
echo "   3. Select xmanya26911-bit/omegacli"
echo "   4. Render auto-detects render.yaml"
echo "   5. Click 'Create Web Service'"
echo ""
echo "Your API will be live at: https://omega-provider.onrender.com"
echo ""
echo "==> Test it:"
echo 'curl https://omega-provider.onrender.com/v1/models'
echo 'curl -X POST https://omega-provider.onrender.com/v1/chat/completions \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '\''{"model":"deepseek-v4-flash-free","messages":[{"role":"user","content":"hi"}]}'\'
echo ""
echo "==> Sell it:"
echo "  - Point your customers to https://omega-provider.onrender.com"
echo "  - Generate API keys: curl -X POST https://omega-provider.onrender.com/v1/api-keys"
echo "  - Rate limit: 60 req/min (change in code)"
