#!/usr/bin/env bash
# Download the 3D scan (Mesh_Tressa.stl, about 1 GB) from the shared Google Drive folder
# "Scan for car part" into the current directory.
set -euo pipefail
SCAN_ID="1lIu-2aQVOOUrLpyvMcIiujVLmZoPQ6Ck"
OUT="Mesh_Tressa.stl"
if [[ -f "$OUT" ]]; then echo "scan already present"; exit 0; fi
curl -fsSL --retry 4 -o "$OUT" "https://drive.usercontent.google.com/download?id=${SCAN_ID}&export=download&confirm=t"
head -c 5 "$OUT" | grep -q "<" && { echo "got an HTML page, the file is not link-shared"; exit 1; } || true
ls -l "$OUT"
