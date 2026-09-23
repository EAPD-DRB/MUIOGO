"""Write a single-page HTML report from a layered across-steps result list, so results can be
opened in a browser and explored variable by variable. Reusable for any run that produces the
layered_results.json shape.

Not fully self-contained: the page loads Chart.js from a public CDN, so a network connection is
required when it is first opened (the rest -- data, styling, layout -- is inlined).
"""
from __future__ import annotations

import html as _html
import json
import os

from . import style

_CDN = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"
# Chart.js palette derived from the editorial categorical cycle (single source of truth in
# style.py) -- steps reuse the cycle in order; the macro vars map to its first four hues.
STEP_COLORS = list(style.CATEGORICAL)
VAR_COLORS = dict(zip(("Y", "C", "K", "L"), style.CATEGORICAL))


def write_html_report(layered, out_path, title="OG-CLEWS across-steps results"):
    solved = [r for r in layered if "macro" in r]
    failed = [r["step"] for r in layered if "macro" not in r]
    steps = [r["step"] for r in solved]
    # the energy-good series (demand response + per-group consumption/energy) are dropped when the run
    # has no isolated energy good (energy channels skipped); emit empty series so the charts degrade.
    has_energy = bool(solved) and all("consumption_by_J" in r for r in solved)
    J = len(solved[0]["consumption_by_J"]) if has_energy else 7
    jlabels = style.income_labels(J)
    payload = {
        "steps": steps,
        "energy_demand": [r["energy_demand_pct"] for r in solved] if has_energy else [],
        "macro": {v: [r["macro"].get(v) for r in solved] for v in ("Y", "C", "K", "L")},
        "revenue": [r["fiscal"]["cons_tax_revenue_pct"] for r in solved],
        "welfare": [r["consumption_by_J"] for r in solved] if has_energy else [],
        "energyJ": [r["energy_by_J"] for r in solved] if has_energy else [],
        "jlabels": jlabels,
        "stepColors": STEP_COLORS[:len(steps)],
        "varColors": VAR_COLORS,
    }
    failed_html = (f'<p class="note">Did not converge (omitted): {", ".join(failed)}</p>'
                   if failed else "")
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#1a1a1a;}}
 h1{{font-size:22px;font-weight:500;}} h2{{font-size:15px;font-weight:500;color:#555;margin:1.5rem 0 .5rem;}}
 .note{{color:#a32d2d;font-size:14px;}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;}}
 .cell{{border:0.5px solid #ddd;border-radius:12px;padding:1rem;}} .full{{grid-column:1/-1;}}
 .wrap{{position:relative;width:100%;height:300px;}}
</style></head><body>
<h1>{title}</h1>{failed_html}
<div class="grid">
 <div class="cell"><h2>energy demand (% vs baseline)</h2><div class="wrap"><canvas id="c_energy" role="img" aria-label="energy demand by step"></canvas></div></div>
 <div class="cell"><h2>government revenue (% change)</h2><div class="wrap"><canvas id="c_rev" role="img" aria-label="government revenue by step"></canvas></div></div>
 <div class="cell full"><h2>macro aggregates (% change)</h2><div class="wrap"><canvas id="c_macro" role="img" aria-label="macro aggregates by step"></canvas></div></div>
 <div class="cell full"><h2>consumption change by income group (one line per step)</h2><div class="wrap" style="height:340px;"><canvas id="c_welfare" role="img" aria-label="consumption change by income group across steps"></canvas></div></div>
 <div class="cell full"><h2>energy-demand change by income group (one line per step)</h2><div class="wrap" style="height:340px;"><canvas id="c_energyJ" role="img" aria-label="energy demand by income group across steps"></canvas></div></div>
</div>
<script src="{_CDN}"></script>
<script>
const D={json.dumps(payload)};
const pct=v=>(v>0?'+':'')+(Math.round(v*1000)/1000)+'%';
const base={{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>pct(c.raw)}}}}}}}};
new Chart(c_energy,{{type:'bar',data:{{labels:D.steps,datasets:[{{data:D.energy_demand,backgroundColor:'#1D9E75',borderRadius:4}}]}},options:base}});
new Chart(c_rev,{{type:'bar',data:{{labels:D.steps,datasets:[{{data:D.revenue,backgroundColor:'#378ADD',borderRadius:4}}]}},options:base}});
new Chart(c_macro,{{type:'bar',data:{{labels:D.steps,datasets:Object.keys(D.macro).map(v=>({{label:v,data:D.macro[v],backgroundColor:D.varColors[v],borderRadius:4}}))}},
 options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:true,position:'top'}},tooltip:{{callbacks:{{label:c=>c.dataset.label+' '+pct(c.raw)}}}}}}}}}});
const DASHES=[[],[6,4],[2,3],[10,4,2,4],[1,3]];  // step 0 solid (baseline); reform steps cycle distinct patterns
const lineSets=key=>D[key].map((row,i)=>({{label:D.steps[i],data:row,borderColor:D.stepColors[i],backgroundColor:D.stepColors[i],borderDash:DASHES[i%DASHES.length],borderWidth:2,pointRadius:3,tension:.25}}));
const lineOpts={{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:true,position:'top'}},tooltip:{{callbacks:{{label:c=>c.dataset.label+': '+pct(c.raw)}}}}}},scales:{{x:{{title:{{display:true,text:'lifetime-income group (lowest to highest)'}}}}}}}};
new Chart(c_welfare,{{type:'line',data:{{labels:D.jlabels,datasets:lineSets('welfare')}},options:lineOpts}});
new Chart(c_energyJ,{{type:'line',data:{{labels:D.jlabels,datasets:lineSets('energyJ')}},options:lineOpts}});
</script></body></html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def write_index(fig_dir, out_path, sections, *, country=None, note=None, title=None):
    """Write the scenario's index.html portal: the cover image followed by every figure grouped
    into `sections`, as one self-contained page that links the PNGs in `fig_dir` with relative
    <img> paths. `sections` is an ordered list of (section_title, [figure_basename, ...]); only
    files that exist on disk are shown, so a partial run degrades gracefully. `out_path` is the
    scenario-folder root (figures live one level down in `fig_dir`). If a `report.html` (the
    interactive Chart.js view) exists in `fig_dir`, it is linked. Works offline -- the images are
    local files alongside the page."""
    out_dir = os.path.dirname(os.path.abspath(out_path))
    try:
        rel = os.path.relpath(fig_dir, out_dir).replace(os.sep, "/")  # e.g. "figures"
    except ValueError:
        # Windows: relpath raises across drive letters (e.g. --fig-dir on D: while index.html is on C:).
        # Fall back to an absolute file path so the <img> links still resolve.
        rel = os.path.abspath(fig_dir).replace(os.sep, "/")
    cname = getattr(country, "name", None) or "Scenario"
    title = title or f"{cname}: coupled OG-Core x CLEWS scenario"

    def _img(src, alt, caption=None):
        cap = f"<figcaption>{_html.escape(caption)}</figcaption>" if caption else ""
        return (f'<figure>{cap}<img src="{_html.escape(src)}" alt="{_html.escape(alt)}" '
                f'loading="lazy"></figure>')

    def _fig(basename):
        return (_img(f"{rel}/{basename}.png", basename)
                if os.path.isfile(os.path.join(fig_dir, f"{basename}.png")) else "")

    blocks = []
    if (cover := _fig("cover")):
        blocks.append(f'<section class="cover">{cover}</section>')
    for sec_title, names in sections:
        imgs = "".join(_fig(n) for n in names)
        if imgs:
            blocks.append(f"<section><h2>{_html.escape(sec_title)}</h2>{imgs}</section>")

    # per-step incidence (figures/per_step/<step>/incidence.png), if present
    per_step = os.path.join(fig_dir, "per_step")
    if os.path.isdir(per_step):
        steps = sorted(d for d in os.listdir(per_step)
                       if os.path.isfile(os.path.join(per_step, d, "incidence.png")))
        cells = "".join(_img(f"{rel}/per_step/{s}/incidence.png", f"{s} incidence",
                             caption=s.replace("_", " ")) for s in steps)
        if cells:
            blocks.append(f'<section><h2>Per-step incidence</h2>{cells}</section>')

    link = ""
    if os.path.isfile(os.path.join(fig_dir, "report.html")):
        link = (f'<a class="ix" href="{_html.escape(rel)}/report.html">Interactive charts '
                f'&rarr;</a>')
    note_html = f'<p class="note">{_html.escape(note)}</p>' if note else ""

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(title)}</title>
<style>
 :root{{--claret:#990F3D;--ink:#222;--sub:#555;--mute:#888;--grid:#e6e6e6;}}
 *{{box-sizing:border-box;}}
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);
  max-width:1100px;margin:0 auto;padding:2rem 1.25rem 4rem;line-height:1.45;}}
 header{{border-top:3px solid var(--claret);padding-top:.5rem;margin-bottom:1rem;}}
 .kicker{{color:var(--claret);font-size:.72rem;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;}}
 h1{{font-size:1.55rem;font-weight:700;margin:.2rem 0 .4rem;}}
 .note{{color:var(--sub);font-size:.85rem;margin:.3rem 0 0;}}
 .ix{{display:inline-block;margin-top:.6rem;color:var(--claret);font-size:.85rem;
  text-decoration:none;font-weight:600;}}
 h2{{font-size:1.05rem;font-weight:700;margin:2.4rem 0 .7rem;padding-bottom:.3rem;
  border-bottom:1px solid var(--grid);}}
 section.cover{{margin:.5rem 0 1rem;}}
 figure{{margin:0 0 1.4rem;}}
 figure img{{width:100%;height:auto;display:block;border:1px solid var(--grid);border-radius:8px;}}
 figcaption{{font-size:.8rem;color:var(--mute);margin-bottom:.3rem;}}
 footer{{margin-top:3rem;color:var(--mute);font-size:.75rem;border-top:1px solid var(--grid);
  padding-top:.6rem;}}
</style></head><body>
<header>
 <div class="kicker">Scenario deck</div>
 <h1>{_html.escape(title)}</h1>
 {note_html}
 {link}
</header>
{''.join(blocks)}
<footer>Open this file in a browser. Figures are in <code>{_html.escape(rel)}/</code>.</footer>
</body></html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    return out_path
