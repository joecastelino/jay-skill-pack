#!/usr/bin/env python3
"""Render the SCT Menu Sales scorecard (PNG + PDF) from the scraped JSON.

Format matches what Kevin gets from Tekion's emailed report:
- Header KPIs: Opcode Labor Gross (SUM) and Opcode Parts Gross (SUM)
- Columns: Advisor/Vehicle, Labor Gross, Parts Gross, Labor Price, Parts Price, Total Gross
Usage: render_scorecard.py [path-to-json]  (defaults to today's file)
"""
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

DATA_DIR = Path("/home/itadmin/tekion-reports/data")


def money(x):
    return f"${x:,.2f}"


def build_html(d):
    rows = d["rows"]
    t = d["totals"]
    by_adv = defaultdict(lambda: {"rows": [], "lg": 0, "pg": 0, "lp": 0, "pp": 0})
    for r in rows:
        a = by_adv[r["advisor"]]
        a["rows"].append(r)
        a["lg"] += r["labor_gross"]
        a["pg"] += r["parts_gross"]
        a["lp"] += r["labor_price"]
        a["pp"] += r["parts_price"]
    advisors = sorted(by_adv.items(), key=lambda kv: -(kv[1]["lg"] + kv[1]["pg"]))
    report_date = rows[0]["ro_created"] if rows else ""
    total_gross = t["labor_gross"] + t["parts_gross"]

    body = ""
    for name, a in advisors:
        n = len(a["rows"])
        body += f"""
        <tr class="adv-row">
          <td class="adv-name">{name}<span class="count">{n} menu{'s' if n > 1 else ''}</span></td>
          <td class="num">{money(a['lg'])}</td>
          <td class="num">{money(a['pg'])}</td>
          <td class="num">{money(a['lp'])}</td>
          <td class="num">{money(a['pp'])}</td>
          <td class="num total">{money(a['lg'] + a['pg'])}</td>
        </tr>"""
        for r in a["rows"]:
            body += f"""
        <tr class="detail">
          <td class="veh">RO {r['ro_number']} · {r['year']} {r['model']} · {r['mileage_in']:,} mi · <span class="op">{r['opcode']}</span></td>
          <td class="num dim">{money(r['labor_gross'])}</td>
          <td class="num dim">{money(r['parts_gross'])}</td>
          <td class="num dim">{money(r['labor_price'])}</td>
          <td class="num dim">{money(r['parts_price'])}</td>
          <td class="num dim">{money(r['labor_gross'] + r['parts_gross'])}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box;
    font-family:'Segoe UI',-apple-system,Helvetica,Arial,sans-serif; }}
body {{ background:#0d1321; width:1150px; padding:30px; color:#e8ecf4; }}
.card {{ background:linear-gradient(160deg,#141c30 0%,#0f1626 100%);
  border:1px solid #243150; border-radius:18px; padding:34px 38px; }}
.head {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px; }}
h1 {{ font-size:25px; font-weight:700; letter-spacing:.3px; }}
.sub {{ color:#8fa3c8; font-size:13.5px; margin-top:5px; }}
.badge {{ background:#e8483f; color:#fff; font-weight:700; font-size:13px;
  padding:7px 14px; border-radius:8px; letter-spacing:.8px; white-space:nowrap; }}
.kpis {{ display:flex; gap:16px; margin:24px 0 28px; }}
.kpi {{ flex:1; background:#1a2440; border:1px solid #2c3b63; border-radius:14px; padding:18px 20px; }}
.kpi .label {{ color:#8fa3c8; font-size:11.5px; text-transform:uppercase;
  letter-spacing:1.1px; margin-bottom:8px; }}
.kpi .val {{ font-size:27px; font-weight:700; }}
.kpi.hero {{ background:linear-gradient(135deg,#21408f,#1b2f66); border-color:#3a5bbf; }}
.kpi.hero .val {{ color:#7fd1ff; }}
table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
col.c-veh {{ width:34%; }}
th {{ text-align:left; color:#8fa3c8; font-size:11px; text-transform:uppercase;
  letter-spacing:.8px; padding:10px 10px; border-bottom:1px solid #2c3b63; }}
th.num, td.num {{ text-align:right; }}
td {{ padding:9px 10px; font-size:14px; overflow:hidden; text-overflow:ellipsis; }}
.adv-row td {{ background:#1a2440; font-weight:600; font-size:15px; border-top:9px solid #0f1626; }}
.adv-row td:first-child {{ border-radius:10px 0 0 10px; white-space:nowrap; }}
.adv-row td:last-child {{ border-radius:0 10px 10px 0; }}
.count {{ color:#8fa3c8; font-weight:400; font-size:12.5px; margin-left:9px; }}
.detail td {{ font-size:12.8px; color:#aab8d4; padding:6px 10px; }}
.veh {{ padding-left:24px !important; white-space:nowrap; }}
.op {{ color:#7fd1ff; font-family:Consolas,monospace; font-size:12px; }}
.dim {{ color:#8fa3c8; }}
.total {{ color:#6ee7a0; }}
.foot {{ margin-top:24px; padding-top:16px; border-top:1px solid #243150;
  display:flex; justify-content:space-between; color:#62739a; font-size:12px; }}
</style></head><body><div class="card">
<div class="head">
  <div><h1>SCT Menu Sales Opened — Daily Scorecard</h1>
  <div class="sub">Stevens Creek Toyota · 4202 Stevens Creek Blvd, San Jose CA · ROs opened {report_date} · TEK maintenance menus, labor &gt; $0</div></div>
  <div class="badge">SCT SERVICE</div>
</div>
<div class="kpis">
  <div class="kpi hero"><div class="label">Opcode Labor Gross (SUM)</div><div class="val">{money(t['labor_gross'])}</div></div>
  <div class="kpi hero"><div class="label">Opcode Parts Gross (SUM)</div><div class="val">{money(t['parts_gross'])}</div></div>
  <div class="kpi"><div class="label">Total Menu Gross</div><div class="val">{money(total_gross)}</div></div>
  <div class="kpi"><div class="label">Menus Sold</div><div class="val">{len(rows)}</div></div>
</div>
<table>
<colgroup><col class="c-veh"><col><col><col><col><col></colgroup>
<tr><th>Advisor / Vehicle</th><th class="num">Labor Gross</th><th class="num">Parts Gross</th>
<th class="num">Labor Price</th><th class="num">Parts Price</th><th class="num">Total Gross</th></tr>
{body}
</table>
<div class="foot">
  <div>Source: Tekion Report Builder · "SCT Menu Sales Opened" · synced {d.get('tekion_sync_time')}</div>
  <div>Generated by Jay · {d.get('pulled_at')}</div>
</div>
</div></body></html>"""


def main():
    jf = (Path(sys.argv[1]) if len(sys.argv) > 1 else
          DATA_DIR / f"sct-menu-sales-opened-{date.today().isoformat()}.json")
    d = json.loads(jf.read_text())
    html = build_html(d)
    tmp = Path("/tmp/sct-scorecard.html")
    tmp.write_text(html)
    stem = jf.stem.replace("sct-menu-sales-opened", "SCT-Menu-Sales-Scorecard")
    png = DATA_DIR / f"{stem}.png"
    pdf = DATA_DIR / f"{stem}.pdf"
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        pg = b.new_page(viewport={"width": 1210, "height": 900})
        pg.goto(f"file://{tmp}")
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(png), full_page=True)
        h = pg.evaluate("document.body.scrollHeight")
        pg.pdf(path=str(pdf), width="1210px", height=f"{h + 20}px",
               print_background=True,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        b.close()
    print(png)
    print(pdf)


if __name__ == "__main__":
    main()
