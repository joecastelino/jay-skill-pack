#!/usr/bin/env python3
"""MoM service gross 7 stores, May vs June-MTD. SEQUENTIAL (throttle-safe).
40 ROs/store/month, avg labor+parts GP/RO scaled by exact closed-RO count.
Proven 2026-06-30: ~3s/RO, no throttle trips, ~25 min for 7 stores x 2 months.
Launch as background + notify_on_complete; invoke python DIRECTLY (not nohup&wrapper).
Edit the MAY/JUN windows + SAMPLE for a different period/precision."""
import sys, json, time, urllib.request, urllib.error, datetime
sys.path.insert(0, "/home/itadmin/tekion-api")
from tekion_client import load_config, get_token
cfg = load_config(); tok = get_token(cfg)
BASE = cfg["base_url"] + "/openapi/v4.0.0"
DEALERS=["st","bt","bc","tl","sv","vc","ar"]
NAMES={"st":"Stevens Creek Toyota","bt":"Blackstone Toyota","bc":"Blackstone Chevy",
       "tl":"Toyota of Lancaster","sv":"Stevens Creek VW","vc":"VW Clovis","ar":"Alfa Romeo SJ"}
SAMPLE=40
OUT="/home/itadmin/tekion-reports/data/mom_gross_result.json"
def H(d): return {"Authorization":f"Bearer {tok}","app_id":cfg["app_id"],
                  "dealer_id":cfg["dealers"][d],"Content-Type":"application/json"}
def msq(y,m,d): return str(int(datetime.datetime(y,m,d).timestamp()*1000))
MAY=(msq(2026,5,1),msq(2026,6,1)); JUN=(msq(2026,6,1),msq(2026,7,1))
def req(method,path,dealer,body=None,tries=5):
    for a in range(tries):
        try:
            data=json.dumps(body).encode() if body is not None else None
            r=urllib.request.Request(BASE+path,data=data,headers=H(dealer),method=method)
            return json.loads(urllib.request.urlopen(r,timeout=40).read())
        except urllib.error.HTTPError as e:
            m=e.read()[:120].decode(errors='ignore')
            if e.code==429: time.sleep(15*(a+1)); continue
            if e.code>=500: time.sleep(3); continue
            return {"_err":f"{e.code} {m}"}
        except Exception: time.sleep(2)
    return {"_err":"exh"}
def get_count(dealer,win):
    d=req("POST","/repair-orders:search",dealer,{"filters":[
        {"field":"closedTime","operator":"BTW","values":list(win)},
        {"field":"status","operator":"IN","values":["CLOSED","INVOICED"]}],"pageSize":50})
    return d.get("meta",{}).get("totalCount",0)
def sample_ids(dealer,win,want,skip=0):
    ids=[];tokn=None
    while len(ids)<want+skip:
        b={"filters":[{"field":"closedTime","operator":"BTW","values":list(win)},
           {"field":"status","operator":"IN","values":["CLOSED","INVOICED"]}],"pageSize":50}
        if tokn: b["paginationToken"]=tokn
        d=req("POST","/repair-orders:search",dealer,b)
        res=d.get("data",{}).get("results",[])
        ids+=[r["documentId"] for r in res]
        tokn=d.get("meta",{}).get("nextPageToken")
        if not tokn or not res: break
    return ids[skip:skip+want]
def ro_gross(dealer,rid):
    lg=pg=0
    jd=req("GET",f"/repair-orders/{rid}/jobs",dealer)
    for j in jd.get("data",{}).get("jobs",[]):
        jid=j.get("id")
        if not jid: continue
        od=req("GET",f"/repair-orders/{rid}/jobs/{jid}/operations",dealer)
        for op in od.get("data",{}).get("roOperations",[]):
            lab=op.get("labor") or {}
            lg+=(lab.get("saleAmount") or 0)-(lab.get("costAmount") or 0)
            oid=op.get("id")
            if not oid: continue
            pd=req("GET",f"/repair-orders/{rid}/jobs/{jid}/operations/{oid}/parts",dealer)
            for p in pd.get("data",{}).get("parts",[]):
                s=p.get("saleAmount")
                if s is None: continue
                pg+=s-(p.get("costAmount") or 0)
    return lg/100.0,pg/100.0
def scan(dealer,tag,win):
    cnt=get_count(dealer,win); ids=sample_ids(dealer,win,SAMPLE)
    labor=[];parts=[]
    for rid in ids:
        l,p=ro_gross(dealer,rid); labor.append(l); parts.append(p)
    n=max(len(labor),1); aL=sum(labor)/n; aP=sum(parts)/n
    print(f"DONE {dealer}_{tag} count={cnt} n={len(labor)} avgL=${aL:,.0f} avgP=${aP:,.0f} projGP=${(aL+aP)*cnt:,.0f}",flush=True)
    return {"count":cnt,"n":len(labor),"avg_labor":aL,"avg_parts":aP,
            "proj_labor":aL*cnt,"proj_parts":aP*cnt,"proj_total":(aL+aP)*cnt}
def main():
    res={}
    for d in DEALERS:
        res[d]={"name":NAMES[d]}
        for tag,win in [("may",MAY),("jun",JUN)]:
            res[d][tag]=scan(d,tag,win); json.dump(res,open(OUT,"w"),indent=1)
    print("ALL DONE",flush=True)
if __name__=="__main__": main()
