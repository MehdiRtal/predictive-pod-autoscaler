#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VALUES="$ROOT/chart/values.yaml"

for pkg in scaler pipeline runtime; do
  ver=$(yq eval -p toml -oy '.project.version' "$ROOT/app/$pkg/pyproject.toml")
  old_ver=$(yq eval ".$pkg.image.tag" "$VALUES")

  if [ "$old_ver" != "$ver" ]; then
    yq eval ".$pkg.image.tag = \"$ver\"" -i "$VALUES"
    echo "$pkg $old_ver -> $ver"
  fi
done
