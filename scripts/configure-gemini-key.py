#!/usr/bin/env python3
"""Secure, interactive Gemini API key setup (local developer credential, never a chat message).

    ./scripts/configure-gemini-key.sh            # set or replace the key (hidden input), optionally switch to Gemini mode
    ./scripts/configure-gemini-key.sh --remove   # delete the stored key and switch back to offline mode

What it does:
  * reads the key with hidden input (getpass): nothing you type or paste is shown;
  * checks it against Google's model catalog (models.list, a metadata call, NOT a generation request, no quota for
    generation) and lists the free-tier Flash models it can use; the key travels only in a request header;
  * stores it in the macOS Keychain (service "airport-investment-intelligence", account "GEMINI_API_KEY") through the
    `security` tool's stdin, so it never appears in a command line, process list, shell history or log;
    if the Keychain is unavailable it falls back to .env with owner-only permissions (chmod 600);
  * writes only NON-secret settings to .env (mode, verified model id), preserving every other line.
The key is never printed, logged or written to any Git-tracked file.
"""
from __future__ import annotations

import getpass
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SERVICE, ACCOUNT = "airport-investment-intelligence", "GEMINI_API_KEY"
ENV = ROOT / ".env"
KEY_RX = re.compile(r"^[A-Za-z0-9_\-.]{20,200}$")


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def list_flash_models(key: str) -> tuple[list[str], str | None]:
    """Free-tier Flash models that support generateContent (metadata call; no generation request)."""
    from airport_agent.models import FREE_TIER_MODEL
    out, url = [], "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200"
    try:
        req = urllib.request.Request(url, headers={"x-goog-api-key": key})
        with urllib.request.urlopen(req, timeout=30, context=_ctx()) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return [], f"the API rejected the key (HTTP {e.code})"
    except Exception as e:                                   # network etc.; never include the key
        return [], f"could not reach the model catalog ({type(e).__name__})"
    for m in data.get("models", []):
        mid = m.get("name", "").removeprefix("models/")
        if "generateContent" in m.get("supportedGenerationMethods", []) and FREE_TIER_MODEL.match(mid):
            out.append(mid)
    return sorted(set(out)), None


def keychain_store(key: str) -> bool:
    if sys.platform != "darwin":
        return False
    cmd = f'add-generic-password -U -a {ACCOUNT} -s {SERVICE} -l "Airport Investment Intelligence Gemini key" -w "{key}"\n'
    r = subprocess.run(["security", "-i"], input=cmd, text=True, capture_output=True)   # key via stdin only
    if r.returncode != 0:
        return False
    from airport_data.config import keychain_secret
    return keychain_secret() == key


def keychain_delete() -> bool:
    r = subprocess.run(["security", "delete-generic-password", "-a", ACCOUNT, "-s", SERVICE], capture_output=True)
    return r.returncode == 0


def env_update(values: dict[str, str | None]) -> None:
    """Set/remove keys in .env, preserving every other line; owner-only permissions."""
    src = ENV if ENV.exists() else ROOT / ".env.example"          # a new .env starts from the documented template
    lines = src.read_text().splitlines() if src.exists() else []
    seen, out = set(), []
    for ln in lines:
        k = ln.split("=", 1)[0].strip().removeprefix("export ").strip() if "=" in ln and not ln.lstrip().startswith("#") else None
        if k in values:
            seen.add(k)
            if values[k] is not None:
                out.append(f"{k}={values[k]}")
            continue
        out.append(ln)
    out += [f"{k}={v}" for k, v in values.items() if k not in seen and v is not None]
    tmp = ENV.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, ENV)
    os.chmod(ENV, 0o600)


def ask(prompt: str, default: bool = True) -> bool:
    a = input(f"{prompt} [{'Y/n' if default else 'y/N'}] ").strip().lower()
    return default if not a else a.startswith("y")


def main() -> int:
    print("\n=== Airport Investment Intelligence: Gemini API key setup ===\n")
    if "--remove" in sys.argv:
        ok = keychain_delete()
        env_update({"GEMINI_API_KEY": None, "AIRPORT_MODEL": "offline", "AIRPORT_ALLOW_GEMINI": None})
        print(("Removed the key from the Keychain. " if ok else "No Keychain item found. ")
              + "Mode set to OFFLINE. Restart the app: ./scripts/start.sh")
        return 0
    print("Paste your Gemini API key (from https://aistudio.google.com/apikey) and press Enter.")
    print("Input is hidden: nothing will appear while you paste or type. It is never shown or logged.\n")
    try:
        key = getpass.getpass("Gemini API key: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Nothing was changed.")
        return 1
    if not KEY_RX.match(key):
        print("\nFAILED: that does not look like an API key (unexpected length or characters). Nothing was saved.")
        return 1
    print("\nChecking the key against Google's model catalog (metadata only, no generation request)...")
    models, err = list_flash_models(key)
    if err:
        print(f"FAILED: {err}. Nothing was saved.")
        return 1
    if not models:
        print("FAILED: the key works but no free-tier Flash model with generateContent is available. Nothing was saved.")
        return 1
    current = os.environ.get("AIRPORT_GEMINI_MODEL") or "gemini-3.8-flash"
    stable = [m for m in models if not re.search(r"preview|exp|lite", m)]
    chosen = current if current in models else (stable or models)[-1]
    print(f"OK: key accepted. Free-tier Flash models available: {', '.join(models)}")
    print(f"Selected model: {chosen}")
    if keychain_store(key):
        where = "macOS Keychain (service 'airport-investment-intelligence')"
        env_update({"GEMINI_API_KEY": None})            # never keep a second copy in .env
    else:
        env_update({"GEMINI_API_KEY": key})
        where = f"{ENV} (owner-only, chmod 600; git-ignored)"
    del key
    (ROOT / "data" / "app").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "app" / "gemini_model_check.json").write_text(json.dumps(
        {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "available_flash_models": models,
         "selected": chosen, "key_storage": "keychain" if "Keychain" in where else "env"}, indent=2))
    print(f"SUCCESS: key saved in {where}.")
    if ask("Switch the app to Gemini mode now?", True):
        env_update({"AIRPORT_MODEL": "gemini", "AIRPORT_ALLOW_GEMINI": "1", "AIRPORT_GEMINI_MODEL": chosen})
        print("Mode set to GEMINI. Offline again any time: ./scripts/mode.sh offline")
    else:
        env_update({"AIRPORT_GEMINI_MODEL": chosen})
        print("Mode unchanged. Switch later: ./scripts/mode.sh gemini")
    print("Restart the app to apply:  ./scripts/start.sh --restart\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
