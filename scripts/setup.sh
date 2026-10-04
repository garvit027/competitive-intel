#!/usr/bin/env bash
# Setup script for Competitive Intelligence Platform

set -euo pipefail

echo "🚀 Setting up Competitive Intelligence Platform..."

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo "❌ Python $REQUIRED_VERSION+ required, found $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "✅ uv available"

# Create virtual environment and install
echo "📦 Installing dependencies..."
uv sync --frozen --all-extras

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
uv run pre-commit install

# Create .env from example if not exists
if [[ ! -f .env ]]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys:"
    echo "   - SERPAPI_API_KEY (get free at https://serpapi.com/manage-api-key)"
    echo "   - OPENAI_API_KEY (or compatible provider)"
else
    echo "✅ .env already exists"
fi

# Create necessary directories
mkdir -p reports data .cache/serpapi logs

# Run basic validation
echo "🔍 Validating installation..."
uv run python -c "import competitive_intel; print('✅ Package imports successfully')"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Run 'make demo' for a quick test"
echo "3. Run 'make run' to see CLI help"
echo "4. Run 'make example-basic' for a basic research example"
echo ""
echo "For Docker deployment:"
echo "  make docker-build && make docker-up"