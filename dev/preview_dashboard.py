"""Assemble a compiled-workflow run into one local dashboard page, laid out
per layout.json (10-column grid), for reviewing outputs outside Ecoscope.
When the run is grouped (e.g. by year), a dropdown switches views the way
the Ecoscope dashboard filter does.

  python dev/preview_dashboard.py [/tmp/incident-reports/output] [--no-open]

Writes <output>/dashboard.html and opens it.
"""

import html
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
OUTPUT = Path(args[0] if args else "/tmp/incident-reports/output")
# Ecoscope Desktop (ecoscope-web WorkflowResultsGridLayout / IframeWidget / StatWidget):
# rowHeight 28, margin 24, card bg #F9F9F9 + border + 6px radius, title bar p-4 with a bottom
# border (iframe widgets), empty p-2 footer under iframes, stat value text-3xl teal.
ROW_PX = 28
GAP_PX = 24

result = json.loads((OUTPUT / "result.json").read_text())
if result.get("error"):
    sys.exit(f"Workflow failed: {result['error']}")
dash = result["result"]
layout = {item["widget_id"]: item for item in json.loads((REPO / "layout.json").read_text())}


def view_label(key: str) -> str:
    return ", ".join(str(v) for v in json.loads(key).values())


def cell_body(w: dict) -> str:
    if w["widget_type"] == "text":
        items = "".join(f"<li>{html.escape(line.lstrip('- '))}</li>" for line in (w["data"] or "").splitlines())
        return f'<ul class="text">{items}</ul>'
    if w["widget_type"] == "stat":
        return f'<p class="stat">{html.escape(str(w.get("data") or "–"))}</p>'
    if not w.get("data"):
        return '<p class="empty">No data for this selection</p>'
    return f'<div class="frame"><iframe src="{Path(w["data"]).name}"></iframe></div><div class="foot"></div>'


views = {}
for key, widgets in sorted(dash["views"].items(), key=lambda kv: view_label(kv[0])):
    cells = []
    if isinstance(widgets, dict):  # newer result.json: {"dashboard": [...]}
        widgets = widgets.get("dashboard", [])
    for i, w in enumerate(widgets):
        pos = layout.get(i, {"x": 0, "y": 1000 + i, "w": 10, "h": 10})
        style = f"grid-column:{pos['x'] + 1}/span {pos['w']};grid-row:{pos['y'] + 1}/span {pos['h']}"
        kind = "statcard" if w["widget_type"] == "stat" else "card"
        cells.append(f'<div class="{kind}" style="{style}"><h3>{html.escape(w["title"])}</h3>{cell_body(w)}</div>')
    views[view_label(key)] = "".join(cells)

labels = list(views)
options = "".join(f'<option value="{html.escape(v)}">{html.escape(v)}</option>' for v in labels)
selector = (
    f'<label class="sel">View <select id="view" onchange="show(this.value)">{options}</select></label>'
    if len(labels) > 1
    else ""
)
meta = dash["metadata"]
page = f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(meta["title"])}</title>
<style>
body{{font-family:Roboto,Helvetica,Arial,sans-serif;margin:0;background:#fafafa;color:#222}}
header{{background:#fff;border-bottom:1px solid #e5e7eb;padding:14px 24px;display:flex;align-items:center;gap:24px}}
header h1{{margin:0;font-size:20px}} header p{{margin:4px 0 0;color:#666;font-size:13px}}
.sel{{margin-left:auto;font-size:13px;color:#444}} .sel select{{margin-left:6px;padding:4px 8px;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(10,1fr);grid-auto-rows:{ROW_PX}px;gap:{GAP_PX}px;padding:24px;max-width:1500px;margin:auto}}
.card,.statcard{{background:#f9f9f9;border:1px solid #dedede;border-radius:6px;display:flex;flex-direction:column;overflow:hidden}}
.card h3,.statcard h3{{margin:0;padding:16px;font-size:16px;font-weight:400;color:#4b5563;line-height:24px}}
.card h3{{border-bottom:1px solid #dedede}}
.frame{{flex:1;position:relative}} .frame iframe{{position:absolute;inset:0;width:100%;height:100%;border:0}} .foot{{height:16px}}
.text{{margin:8px 16px;padding-left:18px;font-size:13px;line-height:1.5;overflow:auto}}
.empty{{margin:auto;color:#999;font-size:13px}} .stat{{margin:0 16px;font-size:30px;line-height:36px;color:#107284;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
</style></head><body>
<header><div><h1>{html.escape(meta["title"])}</h1><p>{html.escape(meta["description"])} · {html.escape(meta["time_range"])}</p></div>{selector}</header>
<div class="grid" id="grid"></div>
<script>
const VIEWS = {json.dumps(views)};
function show(v) {{ document.getElementById("grid").innerHTML = VIEWS[v]; }}
show({json.dumps(labels[0])});
</script></body></html>"""

out = OUTPUT / "dashboard.html"
out.write_text(page)
print(f"Written: {out} ({len(labels)} view(s): {', '.join(labels)})")
if "--no-open" not in sys.argv:
    subprocess.run(["open", str(out)])
