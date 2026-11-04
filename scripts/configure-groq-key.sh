#!/usr/bin/env bash
# Secure Groq key setup (hidden input; own macOS Keychain item). See scripts/configure-groq-key.py.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python scripts/configure-groq-key.py "$@"
