#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd -- "$script_dir/../backend" && pwd)"

if [[ -z "${QAIRLINE_SEED_PASSWORD:-}" ]]; then
  if [[ ! -t 0 ]]; then
    echo "Set QAIRLINE_SEED_PASSWORD when running non-interactively." >&2
    exit 1
  fi
  read -r -s -p "Demo user password (at least 8 characters): " QAIRLINE_SEED_PASSWORD
  printf '\n'
fi

export QAIRLINE_SEED_PASSWORD
export QAIRLINE_SEED_MONGO_URI="${QAIRLINE_SEED_MONGO_URI:-mongodb://127.0.0.1:27017/qairline}"
cd "$backend_dir"
node seed/import-seed.js
