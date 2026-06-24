#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "⚠️  Created .env — add your ANTHROPIC_API_KEY and run again."
  echo "    Get it at: https://console.anthropic.com"
  echo ""
  exit 1
fi

source .env
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "sk-ant-your-key-here" ]; then
  echo "❌ Set ANTHROPIC_API_KEY in .env first"
  exit 1
fi

if ! python3 -c "import flask" 2>/dev/null; then
  echo "📦 Installing dependencies..."
  pip3 install -r requirements.txt -q
fi

echo ""
echo "✅ Outbound Coach running at http://localhost:5051"
echo "   Press Ctrl+C to stop"
echo ""

python3 app.py
