#!/usr/bin/env bash
# Download the 3D scan of the Trinity Force KMX-15 handguard into handguard/work/.
# The scan lives in a public Google Drive file. Photos are not needed for the build.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$HERE/work"
SCAN_ID="14hc4KWcBcMVmhuOQADPWfVS8wDfi0-TJ"
OUT="$WORK/Handguard_JackBeard.stl"

mkdir -p "$WORK"

valid_stl() {
  python3 - "$1" <<'PY'
import os, struct, sys
p = sys.argv[1]
n = os.path.getsize(p)
with open(p, "rb") as f:
    head = f.read(84)
ok = n > 84 and struct.unpack("<I", head[80:84])[0] * 50 + 84 == n
ok = ok or head[:5] == b"solid"
sys.exit(0 if ok else 1)
PY
}

if [[ -f "$OUT" ]] && valid_stl "$OUT"; then
  echo "scan already present: $OUT"
  exit 0
fi

echo "downloading scan..."
curl -fsSL --retry 4 -o "$OUT" \
  "https://drive.usercontent.google.com/download?id=${SCAN_ID}&export=download&confirm=t" || true

if ! valid_stl "$OUT"; then
  echo "direct download failed, trying gdown"
  pip install -q gdown
  gdown --fuzzy "https://drive.google.com/file/d/${SCAN_ID}/view" -O "$OUT"
fi

valid_stl "$OUT"
ls -l "$OUT"
