#!/usr/bin/env python3
"""Tekion ServiceNow KB search & scrape — see SKILL.md. Canonical copy lives at
/home/itadmin/tekion-reports/kb_search_scrape.py (keep both in sync).
Usage:
  python3 kb_search_scrape.py search "bin location"
  python3 kb_search_scrape.py article KB0012192 [KB...]
"""
import requests, json, time, sys, re
B = "http://localhost:9223"

def ev(js, t=40):
    r = requests.post(f"{B}/eval", json={"js": js}, timeout=t)
    try:
        j = r.json(); return j.get("result") if isinstance(j, dict) and "result" in j else j
    except Exception:
        return r.text

def goto(url, wait=7):
    ev(f"window.location.href={json.dumps(url)}"); time.sleep(wait)

def ensure_kb_session():
    goto("https://tekion.service-now.com/sp/en?id=index", 7)
    body = ev("document.body.innerText.slice(0,300)") or ""
    return not ("Login" in body and "Log in" in body and "Joe" not in body)

def find_search_box():
    coords = ev(r"""(function(){var acc=[];var walk=function(r){var els=r.querySelectorAll('input');
    for(var i=0;i<els.length;i++){var e=els[i];if(e.offsetParent!==null){var b=e.getBoundingClientRect();
    acc.push({x:Math.round(b.x+b.width/2),y:Math.round(b.y+b.height/2)})}}
    var all=r.querySelectorAll('*');for(var j=0;j<all.length;j++){if(all[j].shadowRoot)walk(all[j].shadowRoot)}};
    walk(document);return JSON.stringify(acc)})()""")
    try: return json.loads(coords)
    except Exception: return []

def kb_search(query):
    goto("https://tekion.service-now.com/sp/en?id=index", 7)
    boxes = find_search_box()
    if not boxes: return {"error": "search box not found"}
    requests.post(f"{B}/mouse", json={"x": boxes[0]["x"], "y": boxes[0]["y"]}, timeout=10); time.sleep(1.5)
    js = r"""(function(){var a=document.activeElement;
    while(a&&a.shadowRoot&&a.shadowRoot.activeElement){a=a.shadowRoot.activeElement}
    if(!a||a.tagName!=='INPUT')return 'no input';
    var setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
    var q=%s;setter.call(a,'');
    for(var i=0;i<q.length;i++){setter.call(a,q.slice(0,i+1));a.dispatchEvent(new Event('input',{bubbles:true,composed:true}))}
    ['keydown','keypress','keyup'].forEach(function(t){a.dispatchEvent(new KeyboardEvent(t,{bubbles:true,composed:true,key:'Enter',keyCode:13,which:13}))});
    return 'ok'})()""" % json.dumps(query)
    if ev(js) == "no input": return {"error": "could not focus search input"}
    time.sleep(6)
    raw = ev(r"""(function(){var txt='';var walk=function(r){var a=r.querySelectorAll('*');
    for(var i=0;i<a.length;i++){if(a[i].shadowRoot){txt+='\n'+a[i].shadowRoot.textContent;walk(a[i].shadowRoot)}}};
    walk(document);var lines=txt.split('\n').map(function(l){return l.trim()}).filter(function(l){return l.length>6&&l.length<120});
    var seen={};var out=[];lines.forEach(function(l){if(!seen[l]){seen[l]=1;out.push(l)}});return JSON.stringify(out.slice(0,60))})()""")
    try: lines = json.loads(raw)
    except Exception: lines = []
    results = []
    for i, l in enumerate(lines):
        m = re.match(r'^(KB\d{7})$', l)
        if m:
            title = ""
            for j in range(i+1, min(i+4, len(lines))):
                if not re.match(r'^KB\d{7}$', lines[j]) and "ago" not in lines[j].lower():
                    title = lines[j]; break
            results.append({"kb": m.group(1), "title": title})
    return {"query": query, "results": results, "all_lines": lines}

def scrape_article(kb):
    goto(f"https://tekion.service-now.com/sp/en?id=kb_article_view&sysparm_article={kb}", 7)
    url = ev("window.location.href") or ""
    body = ev(r"""(function(){var sel=['.kb-article-content','[itemprop=articleBody]','article','.article-content'];
    for(var s of sel){var e=document.querySelector(s);if(e&&(e.innerText||'').trim().length>30)return e.innerText;}
    return document.body.innerText.slice(0,3000);})()""")
    return {"kb": kb, "url": url, "body": body}

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    if not ensure_kb_session():
        print(json.dumps({"error": "KB not authed. In DMS click Get Help -> Knowledge Base once, then retry."})); sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "search": print(json.dumps(kb_search(" ".join(sys.argv[2:])), indent=2))
    elif cmd == "article": print(json.dumps([scrape_article(k) for k in sys.argv[2:]], indent=2))
    else: print(__doc__)
