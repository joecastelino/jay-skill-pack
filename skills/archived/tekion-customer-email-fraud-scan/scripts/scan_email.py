#!/usr/bin/env python3
"""
Scan all 7 AMG Tekion stores for customer records currently carrying given
email address(es). Detects CSI/survey-redirect fraud. See SKILL.md.

Usage:
    python3 scan_email.py joesclassics2@gmail.com brothapleez@icloud.com

Outputs a per-(store,email) count, then a lastUpdateTime-sorted detail table for
every store with hits, and saves raw + detail JSON under /home/itadmin/.

GOTCHA: send ONLY {"email": addr} — adding count/pagination params returns
HTTP 400 invalid.input.error. email-alone returns 200.
"""
import sys, time, json, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/home/itadmin/tekion-api")
import tekion_client as tk

PT = timezone(timedelta(hours=-7))  # Pacific PDT; use -8 in winter for exactness


def fmt(ms):
    return datetime.fromtimestamp(ms / 1000, PT).strftime("%Y-%m-%d %H:%M PT") if ms else "?"


def name_of(row):
    det = row.get("customerDetails") or {}
    nm = det.get("name") or {}
    n = " ".join(p for p in [nm.get("firstName"), nm.get("lastName")] if p)
    return n or det.get("businessName") or "(no name)"


def search(cfg, did, email):
    tok = tk.get_token(cfg)
    url = cfg["base_url"] + "/openapi/v4.0.0/customers?" + urllib.parse.urlencode({"email": email})
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {tok}", "app_id": cfg["app_id"], "dealer_id": did})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_err": e.code, "_body": e.read().decode()[:200]}


def main(emails):
    cfg = tk.load_config()
    dealers = cfg["dealers"]
    raw, detail = {}, []
    print("=== COUNTS ===")
    for code, did in dealers.items():
        for em in emails:
            out = search(cfg, did, em)
            if "_err" in out:
                print(f"[{code}] {em}: ERR {out['_err']} {out['_body'][:80]}")
                continue
            rows = out.get("data", [])
            total = out.get("meta", {}).get("total", len(rows))
            raw.setdefault(code, {})[em] = total
            flag = " <<<" if total else ""
            print(f"[{code}] {em}: total={total}{flag}")
            for row in rows:
                detail.append({
                    "store": code, "email_on_file": em,
                    "customerId": row.get("id"), "displayId": row.get("displayId"),
                    "status": row.get("status"), "name": name_of(row),
                    "creationTime": row.get("creationTime"),
                    "lastUpdateTime": row.get("lastUpdateTime"),
                })
            time.sleep(0.4)

    detail.sort(key=lambda r: r.get("lastUpdateTime") or 0)
    print("\n=== DETAIL (sorted by lastUpdateTime) ===")
    print(f"{'store':<6}{'lastUpdate':<20}{'created':<20}{'name':<24}{'email':<28}{'displayId'}")
    print("-" * 124)
    for r in detail:
        print(f"{r['store']:<6}{fmt(r['lastUpdateTime']):<20}{fmt(r['creationTime']):<20}"
              f"{r['name'][:23]:<24}{r['email_on_file']:<28}{r['displayId']}")

    json.dump(raw, open("/home/itadmin/survey-fraud-customer-scan.json", "w"), indent=2, default=str)
    json.dump(detail, open("/home/itadmin/survey-fraud-customer-detail.json", "w"), indent=2, default=str)
    print(f"\nTotal current hits: {len(detail)}. Saved raw + detail under /home/itadmin/.")
    print("REMEMBER: count is a FLOOR (reverted edits invisible); API has no modifiedBy/who.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: scan_email.py <email> [email2 ...]"); sys.exit(1)
    main(sys.argv[1:])
