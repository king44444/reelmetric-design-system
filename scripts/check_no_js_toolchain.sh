#!/usr/bin/env bash
# ADR-0054 SS2.3: this repo and its CI stay Python-only. Kept as a standalone
# script (not inlined in .github/workflows/ci.yml) so the literal words this
# check searches for don't themselves live inside the workflow file it's
# meant to keep clean -- an inlined grep would match its own source line.
set -euo pipefail

if find . -name package.json -not -path './.git/*' | grep -q .; then
  echo "FAIL: package.json present"
  exit 1
fi

if grep -rEn 'actions/setup-node|\bnpm install\b|\bnpx \b' .github/workflows/; then
  echo "FAIL: JavaScript toolchain referenced in CI"
  exit 1
fi

echo "NO NODE / CI CLEAN"
