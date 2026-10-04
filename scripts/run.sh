#!/usr/bin/env bash
# Run script for Competitive Intelligence Platform

set -euo pipefail

# Load environment
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default command
COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    research)
        uv run competitive-intel research "$@"
        ;;
    monitor)
        uv run competitive-intel monitor "$@"
        ;;
    demo)
        uv run competitive-intel demo
        ;;
    brief)
        uv run competitive-intel brief "$@"
        ;;
    validate)
        uv run competitive-intel validate "$@"
        ;;
    version)
        uv run competitive-intel version
        ;;
    python)
        uv run python "$@"
        ;;
    pytest)
        uv run pytest "$@"
        ;;
    shell)
        uv run python -c "import competitive_intel; print('Competitive Intel v' + competitive_intel.__version__); print('Ready for interactive use')"
        uv run ipython
        ;;
    *)
        echo "Usage: $0 <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  research <topic> [options]  - Run research task"
        echo "  monitor <topic> [options]   - Start continuous monitoring"
        echo "  demo                        - Run quick demo"
        echo "  brief <topic> -o <file>     - Generate brief template"
        echo "  validate <file>             - Validate brief file"
        echo "  version                     - Show version"
        echo "  python <script.py>          - Run Python script"
        echo "  pytest [args]               - Run tests"
        echo "  shell                       - Start IPython shell"
        echo ""
        echo "Examples:"
        echo "  $0 research \"AI Companies\" --entity \"OpenAI,Anthropic\" --entity-type \"company,company\""
        echo "  $0 monitor \"Cloud Providers\" --entity \"AWS,GCP,Azure\" --interval 60"
        echo "  $0 demo"
        exit 1
        ;;
esac