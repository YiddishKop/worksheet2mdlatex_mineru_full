#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Cross-platform runner (Linux/macOS) for the worksheet2mdlatex pipeline.
# Usage: ./scripts/run_auto.sh [--images_dir images] [--out_dir outputs] [--use_mineru] [--format md|tex|both] [--emit_snippet]

python -m scripts.run_auto "$@"

