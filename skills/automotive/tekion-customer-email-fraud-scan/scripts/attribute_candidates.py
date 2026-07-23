#!/usr/bin/env python3
"""DISCOVERY-MODE attribution: for each shared-email candidate, find WHO created
the ROs for that email's customers (the bad-actor fingerprint).

Input : /home/itadmin/tl-fraud-candidates.json  = [[email, count], ...]
        (the >=3-distinct-customer shared emails from the weekly base scan,
         AFTER excluding dummy placeholders + @<dealer-domain> staff emails)
Output: prints per-email top advisor/creator; checkpoints to tl-candidate-attribution.json

Classify after: creator% = (top creator's count) / ncust
  >=0.85 FRAUD (single-advisor lock) | 0.60-0.85 LIKELY | else EXCLUDE (shared/staff)
Run as BACKGROUND process (notify_on_complete) — many VIN->RO lookups, will exceed 300s inline.
Swap dealer code 'tl' as needed. See SKILL.md for the full 4-step discovery method.
"""
import sys, json, time, urllib.request, urllib.error, urllib.parse
from collections import Counter
sys.path.insert(0, "/home/itadmin/tekion-api")
import tekion_client as tk
cfg = tk.load_config(); did = cfg["dealers"]["tl"]
def tok(): return tk.get_token(cfg)

def cust_by_email(em):
    qs = "?" + urllib.parse.urlencode({"email": em})  # email param ONLY — adding count=400s
    req = urllib.request.Request(cfg["base_url"] + "/openapi/v4.0.0/customers" + qs,
        headers={"Authorization": f"Bearer {tok()}", "app_id": cfg["app_id"], "dealer_id": did})
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=50) as r: return json.loads(r.read()).get("data", [])
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(20 * (a + 1)); continue
            return []
    return []

def ro_search(body):
    req = urllib.request.Request(cfg["base_url"] + "/openapi/v4.0.0/repair-orders:search", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok()}", "app_id": cfg["app_id"], "dealer_id": did}, method="POST")
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(20 * (a + 1)); continue
            return {"_err": e.code}
    return {"_err": "retry"}

name_cache = {}
def uname(uid):
    if not uid or uid == "-1": return "(system)"
    if uid in name_cache: return name_cache[uid]
    try:
        out = tk.api_get(cfg, f"/openapi/v4.0.0/users/{uid}", did)
        dd = out.get("data", {}); cn = (dd.get("userNameDetails") or {}).get("completeNames") or []
        nm = None
        for e in (cn if isinstance(cn, list) else []):  # completeNames is a LIST
            if e.get("nameType") == "DISPLAY_NAME": nm = e.get("value")
        if not nm and cn: nm = cn[0].get("value")
        role = ((dd.get("userRoleDetails") or {}).get("primaryRole") or {}).get("persona")
        emp = (dd.get("employeeDetails") or {}).get("employeeDisplayNumber")
        name_cache[uid] = f"{nm} (#{emp}, {role})" if nm else uid[:8]
    except Exception:
        name_cache[uid] = "(deactivated/unknown)"
    return name_cache[uid]

cands = [c[0] for c in json.load(open("/home/itadmin/tl-fraud-candidates.json"))]
result = {}
for em in cands:
    custs = cust_by_email(em)
    adv = Counter(); cre = Counter(); ncust = 0; cust_names = []
    for cr in custs:
        ncust += 1
        det = cr.get("customerDetails") or {}; nm = det.get("name") or {}
        cust_names.append(" ".join(x for x in [nm.get("firstName"), nm.get("lastName")] if x))
        vins = [v.get("vin") for v in (cr.get("vehicles") or []) if v.get("vin")]
        seen_a = set(); seen_c = set()
        for vin in vins:
            out = ro_search({"filters": [{"field": "vin", "operator": "IN", "values": [vin]}], "pageSize": 50})
            if "_err" in out: continue
            for ro in out.get("data", {}).get("results", []):
                a = ((ro.get("assignee") or {}).get("advisor") or {}).get("id")
                c = (ro.get("createdByUserId") or {}).get("id")
                if a: seen_a.add(a)
                if c: seen_c.add(c)
            time.sleep(0.12)
        for a in seen_a: adv[a] += 1   # count per-CUSTOMER, not per-RO, to avoid heavy-RO bias
        for c in seen_c: cre[c] += 1
    top_adv = [(uname(a), n) for a, n in adv.most_common(3)]
    top_cre = [(uname(c), n) for c, n in cre.most_common(3)]
    result[em] = {"ncust": ncust, "top_advisor": top_adv, "top_creator": top_cre, "sample_names": cust_names[:6]}
    print(f"\n=== {em}  ({ncust} customers) ===", flush=True)
    print(f"  top ADVISOR: {top_adv}", flush=True)
    print(f"  top CREATOR: {top_cre}", flush=True)
    json.dump(result, open("/home/itadmin/tl-candidate-attribution.json", "w"), indent=1, default=str)
print("\nDONE", flush=True)
