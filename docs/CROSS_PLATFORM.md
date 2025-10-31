Cross-Platform Notes (Windows + Ubuntu)

- Python entrypoints are cross-platform. Prefer running via:
  - Windows (PowerShell/CMD): `python -m scripts.run_auto --images_dir images --out_dir outputs [--use_mineru]`
  - Linux/macOS (bash): `./scripts/run_auto.sh --images_dir images --out_dir outputs [--use_mineru]`

- MinerU on a remote Ubuntu worker:
  - On the Windows machine, set environment variable `MINERU_MODE=external` (or `MINERU_SKIP_LOCAL=1`) to skip local MinerU execution.
  - Sync the remote worker’s MinerU outputs back into this repo under `outputs/_mineru_tmp/` (same structure as produced by `scripts/run_mineru.sh`).
  - The pipeline will directly read any pre-generated `*.json` or `*.md` under the corresponding `outputs/_mineru_tmp/<doc>/` folder.

- Requirements
  - `certifi-win32` is Windows-only via an environment marker so `pip` on Ubuntu will ignore it.
  - Pandoc/XeLaTeX are optional. If not found, the pipeline still writes Markdown and LaTeX; PDF export is skipped.

- Convenience wrappers
  - Windows: `scripts/run_mineru.bat`, `scripts/run_to_qs_md.bat`, etc.
  - Linux/macOS: `scripts/run_mineru.sh`, `scripts/run_auto.sh`.

