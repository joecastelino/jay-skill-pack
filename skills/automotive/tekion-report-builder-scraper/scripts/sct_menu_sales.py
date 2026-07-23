#!/usr/bin/env python3
"""
SCT Menu Sales Opened — report scraper.

Pulls the live "SCT Menu Sales Opened" custom report (Report Builder id
695c25173f93ec6865b7138a, dealer 876 / Stevens Creek Toyota) straight out of
Tekion's Report Builder UI, expands all advisor groups, and emits structured
JSON + a formatted summary.

Auth: reuses the canonical session via tekion-auth/login.py artifacts
(.tekion-storage-state.json). Run login.py first if the session is stale.

Output:
  /home/itadmin/tekion-reports/data/sct-menu-sales-opened-<date>.json
  stdout: human-readable summary

Usage:
  /home/itadmin/.hermes/hermes-agent/venv/bin/python3.11 sct_menu_sales.py
"""
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

REPORT_ID = "695c25173f93ec6865b7138a"
REPORT_URL = (f"https://app.tekioncloud.com/report-manager/report/{REPORT_ID}"
              "/reportType/custom/detail")
STORAGE_STATE = "/home/itadmin/caliber-ops/scripts/.tekion-storage-state.json"
OUT_DIR = Path("/home/itadmin/tekion-reports/data")
DEALER_NAME = "Stevens Creek Toyota"

MONEY = re.compile(r"^-?\$[\d,]+\.\d{2}$")
DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{2}$")
GROUP_RE = re.compile(r"^(.+?) \((\d+)\)$")


def log(m):
    print(f"[sct-report] {m}", file=sys.stderr, flush=True)


def switch_dealer(page, name):
    """Switch dealer via popover (real clicks; default after login is BC)."""
    cur = page.evaluate("document.body.innerText.slice(0,400)")
    if name in cur:
        return True
    try:
        page.click("[class*='dealerSelect_container'], [class*='dealerSelect']",
                   timeout=8000)
        time.sleep(1.5)
    except Exception as e:
        log(f"dealer badge click failed: {e}")
    clicked = page.evaluate("""(name) => {
        const roots = document.querySelectorAll(
          '.ant-popover-inner-content, [class*=popover], [class*=dropdown]');
        for (const root of roots) {
            for (const el of root.querySelectorAll('*')) {
                const t = (el.textContent||'').trim();
                if (el.children.length === 0 && t.includes(name)) {
                    el.click(); return t.slice(0,50);
                }
            }
        }
        return null;
    }""", name)
    log(f"dealer switch -> {clicked!r}")
    time.sleep(8)
    return clicked is not None


def expand_all_groups(page):
    """Expand advisor groups in Tekion's custom report table.

    Each group row container holds the label 'Name (N)' AND its expander
    ([class*=expander_expansionCellSize]). After every click the layout
    shifts, so re-locate by GROUP NAME each round and only click groups
    whose child rows aren't all visible yet.
    """
    def state():
        return page.evaluate("""() => {
          const txt = document.body.innerText;
          const dollarRows = txt.split('\\n').filter(
            l => /^\\$[\\d,]+\\.\\d{2}$/.test(l.trim())).length;
          const groups = [];
          document.querySelectorAll('[class*=tRow_bodyRowContainer]').forEach(row => {
            const label = (row.innerText||'').trim().split('\\n')[0];
            const m = label.match(/^(.{2,60}?) \\((\\d+)\\)$/);
            if (!m || /^Total row count/.test(label)) return;
            const exp = row.querySelector('[class*=expander_expansionCellSize]');
            let box = null;
            if (exp) {
              const r = exp.getBoundingClientRect();
              if (r.width > 0 && exp.offsetParent !== null)
                box = {x: r.x + r.width/2, y: r.y + r.height/2};
            }
            groups.push({name: m[1], n: parseInt(m[2]), box});
          });
          return {groups, dollarRows};
        }""")

    def visible_rows_for(name, txt):
        """Count data rows directly under this advisor in the text dump."""
        lines = [l.strip() for l in txt.split("\n") if l.strip()]
        count, active = 0, False
        for l in lines:
            g = GROUP_RE.match(l)
            if g and not DATE_RE.match(l):
                active = (g.group(1) == name)
                continue
            if active and DATE_RE.match(l):
                count += 1
        return count

    for rnd in range(30):
        st = state()
        txt = page.evaluate("document.body.innerText")
        todo = None
        for g in st["groups"]:
            if g["box"] and visible_rows_for(g["name"], txt) < g["n"]:
                todo = g
                break
        if todo is None:
            log(f"all groups expanded ({len(st['groups'])} groups)")
            break
        before = visible_rows_for(todo["name"], txt)
        page.mouse.click(todo["box"]["x"], todo["box"]["y"])
        time.sleep(1.5)
        after_txt = page.evaluate("document.body.innerText")
        after = visible_rows_for(todo["name"], after_txt)
        log(f"group '{todo['name']}': rows {before} -> {after} (want {todo['n']})")
        if after < before:
            # accidentally collapsed — reopen
            st2 = state()
            me = next((x for x in st2["groups"] if x["name"] == todo["name"]), None)
            if me and me["box"]:
                page.mouse.click(me["box"]["x"], me["box"]["y"])
                time.sleep(1.5)
    time.sleep(2)


def parse_report_text(txt):
    """Parse the flat innerText dump into structured rows."""
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    # find table start
    try:
        start = lines.index("Total row count" if "Total row count" in lines else
                            next(l for l in lines if l.startswith("Total row count")))
    except StopIteration:
        start = 0
    rows, advisor = [], None
    i = start
    while i < len(lines):
        l = lines[i]
        g = GROUP_RE.match(l)
        if g and not DATE_RE.match(l):
            advisor = g.group(1)
            i += 1
            continue
        if DATE_RE.match(l) and i + 11 <= len(lines):
            chunk = lines[i:i+11]
            # row layout: date, ro, opcode, year, make, model, mileage, $x4
            if (len(chunk) == 11 and chunk[1].isdigit() and chunk[3].isdigit()
                    and all(MONEY.match(c) for c in chunk[7:11])):
                rows.append({
                    "advisor": advisor,
                    "ro_created": chunk[0],
                    "ro_number": chunk[1],
                    "opcode": chunk[2],
                    "year": int(chunk[3]),
                    "make": chunk[4],
                    "model": chunk[5],
                    "mileage_in": int(chunk[6].replace(",", "")),
                    "labor_gross": float(chunk[7].replace("$", "").replace(",", "")),
                    "parts_gross": float(chunk[8].replace("$", "").replace(",", "")),
                    "labor_price": float(chunk[9].replace("$", "").replace(",", "")),
                    "parts_price": float(chunk[10].replace("$", "").replace(",", "")),
                })
                i += 11
                continue
        i += 1
    return rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True,
                              args=["--no-sandbox", "--disable-dev-shm-usage",
                                    "--disable-gpu"])
        ctx = b.new_context(viewport={"width": 1900, "height": 1200},
                            storage_state=STORAGE_STATE)
        page = ctx.new_page()
        page.goto("https://app.tekioncloud.com/home",
                  wait_until="domcontentloaded", timeout=90000)
        time.sleep(6)
        if "/login" in page.url:
            log("FAIL: session expired — run tekion-auth/login.py first")
            sys.exit(2)
        switch_dealer(page, DEALER_NAME)
        log("opening report")
        page.goto(REPORT_URL, wait_until="domcontentloaded", timeout=90000)
        # poll for report grid (Tekion is slow)
        ok = False
        for _ in range(40):
            txt = page.evaluate("document.body.innerText")
            if "Total row count" in txt:
                ok = True
                break
            time.sleep(2)
        if not ok:
            log("FAIL: report grid never rendered")
            page.screenshot(path="/tmp/sct-report-fail.png")
            sys.exit(3)
        m = re.search(r"(\d+) Record\(s\)", txt)
        expected = int(m.group(1)) if m else None
        log(f"report rendered, expected records: {expected}")
        expand_all_groups(page)
        txt = page.evaluate("document.body.innerText")
        rows = parse_report_text(txt)
        log(f"parsed rows: {len(rows)} (expected {expected})")
        if expected and len(rows) < expected:
            # one more expansion pass
            expand_all_groups(page)
            txt = page.evaluate("document.body.innerText")
            rows = parse_report_text(txt)
            log(f"after retry: {len(rows)}")
        sync_m = re.search(r"Latest successful sync run time:\s*\n(.+)", txt)
        page.screenshot(path=str(OUT_DIR / "last-screen.png"))
        b.close()

    out = {
        "report": "SCT Menu Sales Opened",
        "dealer": DEALER_NAME,
        "report_id": REPORT_ID,
        "pulled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tekion_sync_time": sync_m.group(1).strip() if sync_m else None,
        "expected_records": expected,
        "row_count": len(rows),
        "complete": expected == len(rows),
        "totals": {
            "labor_gross": round(sum(r["labor_gross"] for r in rows), 2),
            "parts_gross": round(sum(r["parts_gross"] for r in rows), 2),
            "labor_price": round(sum(r["labor_price"] for r in rows), 2),
            "parts_price": round(sum(r["parts_price"] for r in rows), 2),
        },
        "rows": rows,
    }
    fp = OUT_DIR / f"sct-menu-sales-opened-{date.today().isoformat()}.json"
    fp.write_text(json.dumps(out, indent=1))
    log(f"saved {fp}")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
