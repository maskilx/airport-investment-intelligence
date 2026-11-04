"""Render docs/images/architecture.svg: the architecture diagram, hand-laid on a fixed grid. Same components and
edges as docs/diagrams/architecture.mmd (the editable structural source; GitHub renders Mermaid natively).

    python3 tools/render_architecture.py              # writes docs/images/architecture.svg
The PNG copy (docs/images/architecture.png) is a 2x browser screenshot of the SVG.
"""
import sys
from xml.sax.saxutils import escape

W, H = 1500, 860
COLX = [70, 410, 750, 1090]            # column left edges, width 300
CW = 300
RAIL = 1444
STY = {
    "ai":  ("#f1ebfd", "#6a46c4", "#2a1760"),
    "det": ("#eef4fd", "#3a6fc0", "#12305e"),
    "val": ("#e8f5ed", "#2b8754", "#0e3a22"),
    "dat": ("#f4f4f1", "#86867e", "#2a2a26"),
    "usr": ("#ffffff", "#2a2a26", "#2a2a26"),
}
out = []
add = out.append


def box(x, y, w, h, title, lines, kind="det", dashed=False, rx=9, tag=None):
    fill, stroke, ink = STY[kind]
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    sw = 2 if kind in ("ai", "val") else 1.3
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}/>')
    n = len(lines)
    ty = y + h / 2 - (n * 16) / 2 + 4
    add(f'<text x="{x + w / 2}" y="{ty}" text-anchor="middle" class="t" fill="{ink}">{escape(title)}</text>')
    for i, ln in enumerate(lines):
        add(f'<text x="{x + w / 2}" y="{ty + 18 + i * 16}" text-anchor="middle" class="b">{escape(ln)}</text>')
    if tag:
        add(f'<text x="{x + w - 10}" y="{y + 15}" text-anchor="end" class="tag" fill="{stroke}">{escape(tag)}</text>')


def band(y, h, label, lx=38):
    add(f'<rect x="22" y="{y}" width="1384" height="{h}" rx="12" fill="#fbfbf9" stroke="#dcdcd5"/>')
    add(f'<text x="{lx}" y="{y + 18}" class="band">{escape(label.upper())}</text>')


def arrow(d, dashed=False, color="#55554f", label=None, lx=0, ly=0, anchor="start"):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6"{dash} marker-end="url(#ah)"/>')
    if label:
        for i, part in enumerate(label.split("\n")):
            add(f'<text x="{lx}" y="{ly + i * 14}" text-anchor="{anchor}" class="lbl">{escape(part)}</text>')


add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">')
add("""<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="#55554f"/></marker>
<style>.t{font-size:15px;font-weight:700}.b{font-size:12.5px;fill:#4a4a44}.band{font-size:11px;font-weight:700;letter-spacing:1.4px;fill:#8a8a82}
.lbl{font-size:12px;fill:#55554f;font-style:italic}.tag{font-size:10px;font-weight:700;letter-spacing:1px}
.leg{font-size:12px;fill:#3a3a35}</style></defs>""")
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

# bands
band(20, 122, "Interface")
band(166, 122, "Agent orchestration")
band(328, 130, "Tools")
band(482, 160, "Analytics and validation")
band(666, 172, "Data foundation", lx=422)

# row 1: interface
box(COLX[0] + 40, 55, 220, 62, "Analyst", ["asks in plain language"], "usr", rx=31)
box(COLX[1], 50, CW, 72, "Chat workspace", ["text chat, live progress,", "evidence inspector"])
box(COLX[2], 50, CW, 72, "FastAPI server", ["conversations, streaming (SSE),", "evidence and provenance API"])
box(COLX[3], 50, CW, 72, "Response rendering", ["answer, Vega-Lite charts,", "evidence, method, limitations"])
arrow(f"M{COLX[0] + 260},86 L{COLX[1] - 4},86")
arrow(f"M{COLX[1] + CW + 2},74 L{COLX[2] - 4},74")
arrow(f"M{COLX[2] - 2},100 L{COLX[1] + CW + 4},100")
arrow(f"M{COLX[3] - 2},86 L{COLX[2] + CW + 4},86")

# row 2: orchestration
box(COLX[1], 195, CW, 72, "Planner", ["LLM (Gemini or Groq), or the", "offline rule-based planner"], "ai", tag="AI")
box(COLX[2], 195, CW, 72, "Agent loop", ["step, tool-call and time budgets;", "progress events"])
box(COLX[3], 195, CW, 72, "Conversation memory", ["entities, findings, assumptions;", "number-free summaries"])
arrow(f"M{COLX[2] + 100},122 L{COLX[2] + 100},191")
arrow(f"M{COLX[2] + 200},191 L{COLX[2] + 200},126", label="events", lx=COLX[2] + 208, ly=162)
arrow(f"M{COLX[1] + CW + 2},224 L{COLX[2] - 4},224")
arrow(f"M{COLX[2] - 2},242 L{COLX[1] + CW + 4},242")
arrow(f"M{COLX[2] + CW + 2},224 L{COLX[3] - 4},224")
arrow(f"M{COLX[3] - 2},242 L{COLX[2] + CW + 4},242")

# legend (row 2, column 1)
lx, ly = COLX[0] + 10, 212
add(f'<text x="{lx}" y="{ly}" class="band">KEY</text>')
for i, (k, name) in enumerate([("ai", "AI (language model)"), ("det", "Deterministic code"),
                               ("val", "Validation"), ("dat", "Data")]):
    fill, stroke, _ = STY[k]
    cx, cy = lx + (i % 2) * 150, ly + 12 + (i // 2) * 22
    add(f'<rect x="{cx}" y="{cy}" width="18" height="14" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    add(f'<text x="{cx + 26}" y="{cy + 11}" class="leg">{name}</text>')
add(f'<path d="M{lx},{ly + 64} L{lx + 30},{ly + 64}" stroke="#55554f" stroke-width="1.6" stroke-dasharray="5 4"/>')
add(f'<text x="{lx + 38}" y="{ly + 68}" class="leg">feedback or live path</text>')

# planner -> tools bus
cx = [x + CW / 2 for x in COLX]
add(f'<path d="M{cx[1]},267 L{cx[1]},308" fill="none" stroke="#55554f" stroke-width="1.6"/>')
add(f'<path d="M{cx[0]},308 L{cx[3]},308" fill="none" stroke="#55554f" stroke-width="1.6"/>')
for c in cx:
    arrow(f"M{c},308 L{c},352")
add(f'<text x="{cx[1] + 8}" y="300" class="lbl">tool calls</text>')

# row 3: tools
box(COLX[0], 356, CW, 82, "Resolve places", ["airport codes, cities, regions;", "asks when ambiguous"])
box(COLX[1], 356, CW, 82, "Run analysis", ["aggregate, rank, trend, anomaly,", "forecast vs actual, screen"])
box(COLX[2], 356, CW, 82, "Context", ["constraint records, data gaps,", "recall, live FAA status"])
box(COLX[3], 356, CW, 82, "Compose answer", ["{F#} placeholders and", "typed claims"])

# row 4: analytics + validation
box(COLX[0], 512, CW, 80, "Semantic layer", ["metric definitions compiled to", "ratio-of-sums SQL"])
box(COLX[1], 512, CW, 80, "Opportunity screen", ["weights and fixed anchors", "from config/screening.toml"])
box(COLX[2], 512, CW, 80, "Findings  F#", ["value, period, inputs,", "sources, caveats"])
box(COLX[3], 512, CW, 80, "Validator", ["numbers only from findings;", "relations and ranks checked by code"], "val")
arrow(f"M{cx[1] + 40},438 L{cx[1] + 40},508")
arrow(f"M{cx[1] - 80},438 L{cx[0] + 90},508")
arrow(f"M{COLX[0] + CW + 2},540 L{COLX[1] - 4},540")
arrow(f"M{COLX[1] + CW + 2},552 L{COLX[2] - 4},552")
arrow(f"M{cx[0]},592 C{cx[0]},630 {cx[2]},630 {cx[2]},596")
arrow(f"M{COLX[2] + CW + 2},552 L{COLX[3] - 4},552")
arrow(f"M{cx[3] - 40},438 L{cx[3] - 40},508")
arrow(f"M{cx[3] + 40},512 L{cx[3] + 40},442", dashed=True, label="rejected:\nerrors to planner", lx=cx[3] + 50, ly=470)

# accepted answer -> chat workspace (right rail)
arrow(f"M{COLX[3] + CW + 2},572 L{RAIL},572 L{RAIL},86 L{COLX[3] + CW + 4},86")
add(f'<text x="{RAIL + 16}" y="{363}" class="lbl" text-anchor="middle" transform="rotate(-90 {RAIL + 16} 363)">accepted: validated answer</text>')

# row 5: data
box(COLX[0], 706, CW, 96, "DuckDB", ["conformed views over immutable,", "checksummed data versions;", "full data or bundled demo subset"], "dat")
box(COLX[1], 718, CW, 72, "Ingestion", ["fetch, checksum, blocking", "validation, atomic build"], "dat")
box(COLX[2], 692, CW, 66, "Public data", ["BTS T-100, On-Time; FAA TAF,", "ACAIS, ATADS; BEA, Census"], "dat")
box(COLX[2], 766, CW, 60, "Curated records", ["caps, curfews, capacity rates"], "dat")
box(COLX[3], 718, CW, 72, "FAA NAS Status", ["live public API, cited as", "external evidence"], "dat", dashed=True)
arrow(f"M{COLX[2] - 2},725 L{COLX[1] + CW + 4},745")
arrow(f"M{COLX[2] - 2},796 L{COLX[1] + CW + 4},768")
arrow(f"M{COLX[1] - 2},754 L{COLX[0] + CW + 4},754")
arrow(f"M{COLX[0] - 2},552 L46,552 L46,754 L{COLX[0] - 4},754", label="SQL", lx=30, ly=650, anchor="middle")
arrow(f"M{COLX[2] + CW - 30},438 L{COLX[2] + CW - 30},462 L1070,462 L1070,754 L{COLX[3] - 4},754", dashed=True)

add("</svg>")
import pathlib
target = sys.argv[1] if len(sys.argv) > 1 else str(pathlib.Path(__file__).resolve().parents[1] / "docs/images/architecture.svg")
open(target, "w").write("\n".join(out))
print("wrote", target)
