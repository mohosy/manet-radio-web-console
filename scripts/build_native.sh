#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cc -O2 -fPIC -shared "$ROOT_DIR/native/link_quality.c" -o "$ROOT_DIR/native/liblink_quality.so"
echo "Built native/liblink_quality.so"
