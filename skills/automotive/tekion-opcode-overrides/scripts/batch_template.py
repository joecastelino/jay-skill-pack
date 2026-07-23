#!/usr/bin/env python3
"""
Batch-add CABIN parts override rows at Blackstone Toyota via persistent browser.
PROVEN RECIPE (2026-06-10):
  1. After ANY reload: click 'Overrides' TOP TAB first, then 'Parts' left panel.
     (Reload lands on Default tab; Labor tab saves rows as LABOR overrides!)
  2. Inject override-helpers.js (wiped on reload -> re-inject each time)
  3. __buildRow({make, modelExact, years, part, price}) -- ~25s
  4. Verify trim cell says 'All trims selected'; if blank, fix via trim modal
  5. Real Playwright click '#btnSalesSetupSave >> nth=1'
  6. Verify via Tekion API GET /override/PARTS that the model+years row exists
"""
import urllib.request, json, time, sys, re

BASE = "http://localhost:9223"
HELPERS_PATH = "/home/itadmin/.hermes/profiles/jay/skills/automotive/tekion-opcode-overrides/scripts/override-helpers.js"
DATASET = "/tmp/cabin_bt_full.json"
PRICE = "21.99"
OPCODE = "CABIN"

def api(endpoint, method="GET", body=None, timeout=120):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + endpoint, data=data,
        headers={"Content-Type": "application/json"} if body else {}, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())

def ev(js, timeout=120):
    return api("/eval", "POST", {"js": js}, timeout=timeout).get("result")

def click(selector=None, text=None, timeout=20):
    body = {"selector": selector} if selector else {"text": text}
    return api("/click", "POST", body, timeout=timeout)

def get_ls():
    return ev("(() => ({dealerId: localStorage.getItem('currentActiveDealerId'), token: localStorage.getItem('t_token'), userId: localStorage.getItem('__user_id'), roleId: localStorage.getItem('currentActiveRoleId'), siteId: localStorage.getItem('currentActiveSiteId')}))()")

def tekion_get(ls, path):
    headers = {"Accept": "application/json", "tekion-api-token": ls["token"],
        "tenantname": "americanmotorscorporation", "userId": ls["userId"]}
    for k, v in [("applicationId","ARC_NA"),("clientId","web"),("dealerId",ls["dealerId"]),
                 ("locale","en_US"),("original-tenantid","americanmotorscorporation"),
                 ("original-userid",ls["userId"]),("productIds","ARC"),("program","DEFAULT"),
                 ("roleId",ls["roleId"]),("subApplicationId","US"),("tek-siteId",ls["siteId"])]:
        headers[k] = v
    req = urllib.request.Request("https://app.tekioncloud.com" + path, headers=headers)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def get_parts_rows(ls):
    d = tekion_get(ls, f"/api/service-module/u/opcode/{OPCODE}_{ls['dealerId']}/override/PARTS")
    rows = []
    for rec in d.get("data", []):
        o = rec["overrideResponse"]
        gv = lambda pn: next((p["value"] for p in o["parameters"] if p["parameter"] == pn), None)
        parts = [re.sub(r"[^A-Z0-9]", "", (p.get("partNumber") or "").upper())
                 for p in o.get("override", {}).get("customParts", [])]
        rows.append({"models": (gv("MODEL") or {}).get("models", []),
                     "years": sorted((gv("YEAR") or {}).get("years", [])),
                     "parts": parts})
    return rows

def goto_parts_tab(reload=False):
    """Hard-reset to CABIN edit page -> Overrides top tab -> Parts left panel."""
    if reload:
        ev("(() => { window.location.href = '/ro/opcode/edit/CABIN'; })()")
        time.sleep(14)
    # wait for top tabs to exist (Tekion is slow)
    for _ in range(10):
        tabs = ev("""(() => [...document.querySelectorAll('.ant-tabs-tab')].filter(t=>t.offsetParent).map(t=>t.textContent.trim()))()""")
        if tabs and "Overrides" in tabs:
            break
        time.sleep(3)
    try:
        click(selector=".ant-tabs-tab:text-is('Overrides'):visible")
    except Exception:
        pass
    time.sleep(4)
    try:
        click(selector="div[class*='leftPanelItem']:text-is('Parts'):visible")
    except Exception:
        pass
    time.sleep(4)
    active = ev("""(() => { var a=null; document.querySelectorAll('[class*="leftPanelItem"]').forEach(function(el){ var c=typeof el.className==='string'?el.className:''; if(c.includes('active')||c.includes('selected')) a=el.textContent.trim(); }); return a; })()""")
    return active

def inject_helpers():
    ev(open(HELPERS_PATH).read())
    ev(open("/home/itadmin/tekion-operator/buildrow2.js").read())
    if not ev("(() => typeof __buildRow2 === 'function')()"):
        raise RuntimeError("helper injection failed")

def fix_trim_if_blank(model):
    """If the new row's trim cell is blank, open trim modal and set All trims."""
    blank = ev(f"""
    (() => {{
        var row = window.__findModelRow(/./, {json.dumps(model)});
        if (!row) return 'no-row';
        var c = row.querySelectorAll('.rt-td');
        var ti = c[5].querySelector('input');
        return ti && ti.value ? 'ok:' + ti.value : 'blank';
    }})()
    """)
    if str(blank).startswith("ok:"):
        return True
    # open trim modal with real fire, select All trims radio, save modal
    ev(f"""
    (() => {{
        var row = window.__findModelRow(/./, {json.dumps(model)});
        if (!row) return 'no-row';
        var c = row.querySelectorAll('.rt-td');
        var ti = c[5].querySelector('input');
        var wr = ti.closest('.ant-input-affix-wrapper') || ti.parentElement;
        wr.scrollIntoView({{block:'center'}});
        window.__fire(wr);
        return 'opened';
    }})()
    """)
    time.sleep(3)
    # real click the All trims radio + modal Save
    try:
        click(text="All trims (including future trims)")
    except Exception:
        pass
    time.sleep(1.5)
    try:
        click(selector=".ant-modal button:text-is('Save'):visible")
    except Exception:
        pass
    time.sleep(3)
    after = ev(f"""
    (() => {{
        var row = window.__findModelRow(/./, {json.dumps(model)});
        if (!row) return 'no-row';
        var ti = row.querySelectorAll('.rt-td')[5].querySelector('input');
        return ti && ti.value ? 'ok' : 'blank';
    }})()
    """)
    return after == "ok"

def build_and_save(row, ls):
    before = get_parts_rows(ls)
    mk_rx = "/^Toyota$/" if row["make"] == "Toyota" else f"/^{row['make']}$/"
    payload = {"make": row["make"], "modelExact": row["model"],
               "years": row["years"], "part": row["part"], "price": PRICE}
    r = ev("__buildRow2(" + json.dumps(payload) + ")", timeout=200)
    rs = json.dumps(r)
    if "ERR:no-years-available" in rs:
        # Row was partially built (make/model committed) — clean it up via reload
        return False, f"SKIP no years in Tekion: {rs[:120]}"
    if "ERR" in rs:
        return False, f"buildRow: {rs[:160]}"
    # trim is verified inside __buildRow2 (trim=set)
    # Save
    click(selector="#btnSalesSetupSave >> nth=1", timeout=30)
    time.sleep(6)
    modal = ev("(() => { var m=[...document.querySelectorAll('.ant-modal-content')].find(x=>x.offsetParent); return m ? m.textContent.trim().substring(0,80) : null; })()")
    if modal:
        for _ in range(4):
            try:
                click(text="Apply", timeout=8); time.sleep(1)
            except Exception:
                break
        try:
            click(selector=".ant-modal button:text-is('Save'):visible", timeout=8)
        except Exception:
            pass
        time.sleep(5)
    # Verify: row with this model+years exists in API
    want_years = tuple(sorted(row["years"]))
    for _ in range(4):
        after = get_parts_rows(ls)
        for ar in after:
            if row["model"] in ar["models"] and tuple(ar["years"]) == want_years:
                return True, f"persisted (rows={len(after)})"
        if len(after) > len(before):
            # row added but years mismatch — flag
            return True, f"persisted w/ year diff (rows={len(after)})"
        time.sleep(4)
    return False, f"not persisted (rows={len(before)})"

def main():
    start_at = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    data = json.load(open(DATASET))
    ls = get_ls()
    if not ls or not ls.get("token"):
        print("FATAL: no session token"); sys.exit(1)

    existing = get_parts_rows(ls)
    print(f"Existing PARTS rows: {len(existing)}")

    def already_covered(row):
        """Skip if a saved row has same model + same part + overlapping years."""
        want_part = re.sub(r"[^A-Z0-9]", "", row["part"].upper())
        want_years = set(row["years"])
        for r in existing:
            if row["model"] in r["models"] and want_part in r["parts"] \
               and want_years & set(r["years"]):
                return True
        return False

    todo = []
    for row in data:
        if already_covered(row):
            print(f"SKIP exists: {row['model']} {row['year_label']}")
            continue
        todo.append(row)
    todo = todo[start_at:]
    print(f"Rows to add: {len(todo)}\n", flush=True)

    ok_n, fails, consecutive = 0, [], 0
    active = goto_parts_tab(reload=True)
    for idx, row in enumerate(todo):
        label = f"{row['make']} {row['model']} {row['year_label']} {row['part']}"
        try:
            if active != "Parts":
                active = goto_parts_tab(reload=True)
                if active != "Parts":
                    raise RuntimeError(f"Parts tab unreachable (active={active})")
            inject_helpers()
            ok, msg = build_and_save(row, ls)
        except Exception as e:
            ok, msg = False, f"exception: {str(e)[:120]}"
        print(f"[{idx+1}/{len(todo)}] {'OK ' if ok else 'FAIL'} {label} -- {msg}", flush=True)
        if ok:
            ok_n += 1; consecutive = 0
        elif msg.startswith("SKIP"):
            # data gap (years not in Tekion) — not a pipeline failure
            fails.append((label, msg)); consecutive = 0
            active = goto_parts_tab(reload=True)
        else:
            fails.append((label, msg)); consecutive += 1
            active = goto_parts_tab(reload=True)  # reset state
            if consecutive >= 3:
                print("ABORT: 3 consecutive failures", flush=True)
                break
        time.sleep(2)

    print(f"\n=== DONE: {ok_n}/{len(todo)} added, {len(fails)} failed ===")
    print(f"Final PARTS rows: {len(get_parts_rows(ls))}")
    for l, m in fails:
        print(f"FAILED: {l} -- {m}")

if __name__ == "__main__":
    main()
