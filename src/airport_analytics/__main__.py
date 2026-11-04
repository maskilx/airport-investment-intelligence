"""Terminal access to the agent tools (used by reviewers, evals and external agents).

    python -m airport_analytics tools                                  # list tool schemas
    python -m airport_analytics call <tool> '<json args>' [--session S]  # call a tool; S persists findings between calls
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

from .tools import TOOLS, Session, tool_schemas


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "tools":
        print(json.dumps(tool_schemas(), indent=1))
        return 0
    if argv[0] != "call" or len(argv) < 3:
        print(__doc__)
        return 2
    name, args = argv[1], json.loads(argv[2])
    sess_path = Path(argv[argv.index("--session") + 1]) if "--session" in argv else None
    s = Session()
    if sess_path and sess_path.exists():
        st = pickle.loads(sess_path.read_bytes())
        s.ctx.store = st
    out = s.call(name, args)
    if sess_path:
        sess_path.write_bytes(pickle.dumps(s.ctx.store))
    if isinstance(out, dict) and "markdown" in out:
        print(out["markdown"])
    else:
        print(json.dumps(out, indent=1, default=str))
    return 1 if isinstance(out, dict) and out.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
