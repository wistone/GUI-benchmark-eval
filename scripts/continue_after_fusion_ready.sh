#!/usr/bin/env bash
set -euo pipefail
ROOT="/Users/shijianping/Work/GUI-benchmark-eval"
cd "$ROOT"

VMRUN="/Applications/VMware Fusion.app/Contents/Library/vmrun"
if [[ ! -x "$VMRUN" ]]; then
  echo "vmrun_missing: install/open VMware Fusion first and complete macOS approval prompts."
  exit 1
fi
export PATH="/Applications/VMware Fusion.app/Contents/Library:$PATH"
"$VMRUN" -T fusion list
source external/OSWorld/.venv/bin/activate
python scripts/osworld_vm_smoke.py --headless
