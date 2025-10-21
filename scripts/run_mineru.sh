#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
mkdir -p outputs
python -m src.pipeline --images_dir images --out_dir outputs --format both --use_mineru
echo "[OK] Done. See outputs/"
