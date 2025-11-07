#!/bin/bash
set -e

echo "🔧 Setting up social-sim monolith..."

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating venv..."
    python3 -m venv "$VENV_DIR"
fi

echo "🚀 Installing dependencies..."
"$VENV_DIR/bin/pip" install -q --upgrade pip
"$VENV_DIR/bin/pip" install -q -r requirements.txt

mkdir -p outputs data_files

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  source .venv/bin/activate"
echo "  cp .env.example .env && edit with your OPENROUTER_API_KEY"
echo "  python monolith.py 'US Constitutional Convention'"
