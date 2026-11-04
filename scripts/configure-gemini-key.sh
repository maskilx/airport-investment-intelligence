#!/usr/bin/env bash
# Secure Gemini key setup (hidden input; stored in the macOS Keychain). See scripts/configure-gemini-key.py.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python scripts/configure-gemini-key.py "$@"
