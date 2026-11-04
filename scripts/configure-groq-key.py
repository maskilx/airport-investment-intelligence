#!/usr/bin/env python3
"""Secure, interactive Groq API key setup. Same standard as the Gemini helper; separate credential and settings.

    ./scripts/configure-groq-key.sh            # set or replace the Groq key (hidden input)
    ./scripts/configure-groq-key.sh --remove   # delete it (the Gemini key is never touched)

* hidden input (getpass): nothing typed or pasted is shown;
* checks the key with GET /openai/v1/models (a catalog lookup, NOT a generation request) and confirms which supported
  tool-calling models (docs/model-provider-review.md) the account can use;
* stores it in the macOS Keychain under its own service 'airport-investment-intelligence-groq' via `security -i`
  stdin, so it never appears in argv, process lists, shell history or logs; .env (chmod 600) only as a fallback;
* writes only non-secret settings to .env, preserving every other line (Gemini settings included).
"""
from __future__ import annotations

import getpass
import json
import os
import re
import runpy
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SERVICE, ACCOUNT = "airport-investment-intelligence-groq", "GROQ_API_KEY"
KEY_RX = re.compile(r"^[A-Za-z0-9_\-.]{20,200}$")
_helper = runpy.run_path(str(ROOT / "scripts" / "configure-gemini-key.py"), run_name="helper")
env_update, ask, ENV = _helper["env_update"], _helper["ask"], _helper["ENV"]


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def available_models(key: str) -> tuple[list[str], str | None]:
    from airport_agent.models import GROQ_MODELS
    req = urllib.request.Request("https://api.groq.com/openai/v1/models",
                                 headers={"Authorization": f"Bearer {key}", "User-Agent": "airport-intel"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ctx()) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return [], f"the API rejected the key (HTTP {e.code})"
    except Exception as e:                                    # never include the key
        return [], f"could not reach the Groq model catalog ({type(e).__name__})"
    ids = {m.get("id") for m in data.get("data", []) if m.get("active", True)}
    return [m for m in GROQ_MODELS if m in ids], None


def keychain_store(key: str) -> bool:
    if sys.platform != "darwin":
        return False
    cmd = f'add-generic-password -U -a {ACCOUNT} -s {SERVICE} -l "Airport Investment Intelligence Groq key" -w "{key}"\n'
    r = subprocess.run(["security", "-i"], input=cmd, text=True, capture_output=True)      # key via stdin only
    if r.returncode != 0:
        return False
    from airport_data.config import keychain_secret
    return keychain_secret(SERVICE, ACCOUNT) == key


def main() -> int:
    print("\n=== Airport Investment Intelligence: Groq API key setup ===\n")
    if "--remove" in sys.argv:
        r = subprocess.run(["security", "delete-generic-password", "-a", ACCOUNT, "-s", SERVICE], capture_output=True)
        env_update({"GROQ_API_KEY": None, "AIRPORT_ALLOW_GROQ": None,
                    **({"AIRPORT_MODEL": "offline"} if os.environ.get("AIRPORT_MODEL") == "groq" else {})})
        print(("Removed the Groq key from the Keychain." if r.returncode == 0 else "No Groq Keychain item found.")
              + " The Gemini key is untouched. Restart the app: ./scripts/start.sh --restart")
        return 0
    print("Paste your Groq API key (from https://console.groq.com/keys) and press Enter.")
    print("Input is hidden: nothing will appear while you paste or type. It is never shown or logged.\n")
    try:
        key = getpass.getpass("Groq API key: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Nothing was changed.")
        return 1
    if not KEY_RX.match(key):
        print("\nFAILED: that does not look like an API key (unexpected length or characters). Nothing was saved.")
        return 1
    print("\nChecking the key against Groq's model catalog (metadata only, no generation request)...")
    models, err = available_models(key)
    if err:
        print(f"FAILED: {err}. Nothing was saved.")
        return 1
    if not models:
        print("FAILED: the key works but none of the supported tool-calling models is available to this account.")
        return 1
    chosen = "openai/gpt-oss-120b" if "openai/gpt-oss-120b" in models else models[0]
    print(f"OK: key accepted. Supported models available to this account: {', '.join(models)}")
    print(f"Selected model: {chosen}")
    if keychain_store(key):
        where = f"macOS Keychain (service '{SERVICE}', separate from the Gemini key)"
        env_update({"GROQ_API_KEY": None})
    else:
        env_update({"GROQ_API_KEY": key})
        where = f"{ENV} (owner-only, chmod 600; git-ignored)"
    del key
    (ROOT / "data" / "app").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "app" / "groq_model_check.json").write_text(json.dumps(
        {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "available_supported_models": models,
         "selected": chosen, "key_storage": "keychain" if "Keychain" in where else "env"}, indent=2))
    print(f"SUCCESS: key saved in {where}.")
    if ask("Switch the app to Groq mode now?", False):
        env_update({"AIRPORT_MODEL": "groq", "AIRPORT_ALLOW_GROQ": "1", "AIRPORT_GROQ_MODEL": chosen})
        print("Mode set to GROQ. Back to Gemini or offline: ./scripts/mode.sh gemini | offline")
    else:
        env_update({"AIRPORT_ALLOW_GROQ": "1", "AIRPORT_GROQ_MODEL": chosen})
        print("Mode unchanged. Switch later: ./scripts/mode.sh groq")
    print("Restart the app to apply:  ./scripts/start.sh --restart\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
