#!/usr/bin/env python3
"""Tekion menu "missing items" audit — ANY store, ANY menu.

Usage:  python3 menu_audit.py <MENU_ID> <DEALER_ID>
Example: python3 menu_audit.py 65530c2cd0e3ef410082bb2c 1251

Runs all three missing-items checks in one pass:
  1. TIER COVERAGE  - combos where factory is suppressed and nothing replaces it
  2. BASE INTERVAL  - rows whose baseSystemInterval != the menu's own interval
  3. ROW SCOPE      - prints each row's make/trim/year scope to eyeball fall-through

Reads over plain urllib with cached headers — no browser, no session contention.
NOTE: if /tmp/tekion_rec_headers.json is scoped to a different dealer, the
included-service NAME lookups will 404. The tier-flag structure still reads fine,
which is all the coverage audit needs — don't let those 404s stop you.
"""
import json, sys, time, urllib.request

MENU_ID   = sys.argv[1]
DEALER_ID = sys.argv[2]

HDRS = dict(json.load(open('/tmp/tekion_rec_headers.json')))
HDRS['dealerId']   = str(DEALER_ID)
HDRS['tek-siteId'] = f'-1_{DEALER_ID}'

BASE = 'https://app.tekioncloud.com/api/service-module/u/opcode'
COMBOS = [(p, c) for p in ('BASIC', 'PREMIUM', 'VALUE')
                 for c in ('NORMAL', 'SEVERE')]


def get(url):
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


_cache = {}
def resolve(ref):
    """referenceId -> (name, opcode). Tolerates 404 under a mismatched dealer."""
    if ref not in _cache:
        try:
            dd = get(f'{BASE}/included-service/{ref}').get('data') or {}
            _cache[ref] = (dd.get('name'), dd.get('opcode'))
        except Exception as e:
            _cache[ref] = (f'<unresolved: {e}>', '?')
        time.sleep(0.25)
    return _cache[ref]


cfg = get(f'{BASE}/service-menu/{MENU_ID}')
d = cfg.get('data') or {}
intervals = d.get('intervals') or []
rows = sorted(d.get('menus') or [], key=lambda r: (r.get('order') or 0))

print(f"menu id    : {d.get('id')}")
print(f"intervals  : {intervals}")
print(f"status     : {d.get('menuStatus') or d.get('status')}")
print(f"rows       : {len(rows)}")

out = json.dumps(cfg)
open(f'/tmp/menu-{MENU_ID}.json', 'w').write(out)
print(f"saved      : /tmp/menu-{MENU_ID}.json")

expected = intervals[0] if len(intervals) == 1 else None
problems = []

for r in rows:
    order = r.get('order')
    params = {p.get('parameter'): p.get('value') for p in (r.get('parameters') or [])}
    make = (params.get('MAKE') or {}).get('makes')
    trim = (params.get('TRIM') or {}).get('standardTrimFilterDetails') or {}
    yr = params.get('YEAR') or {}
    yrs = 'ALL_YEARS' if yr.get('allValues') else yr.get('years')
    bsi = r.get('baseSystemInterval')

    print(f"\n=== ROW {order} | base={bsi} | make={make} | trim={trim} | years={yrs}")

    # --- CHECK 2: base interval stamp -------------------------------------
    if expected and str(bsi) != str(expected):
        msg = (f"ROW {order}: baseSystemInterval={bsi} but menu interval={expected}"
               f"  <-- WRONG FACTORY PACKAGE WILL RENDER")
        print('   !! ' + msg)
        problems.append(msg)

    svcs = (r.get('servicesMetaData') or {}).get('services') or []
    if not svcs:
        print('   (no services on this row)')
        continue

    # --- service inventory + CHECK 1: tier coverage ------------------------
    coverage = {c: [] for c in COMBOS}
    for s in svcs:
        ref, typ = s.get('referenceId'), s.get('type')
        name, op = resolve(ref)
        tiers = [(t.get('packageType'), t.get('drivingCondition'))
                 for t in (s.get('tierMappings') or []) if t.get('enabled')]
        for key in tiers:
            if key in coverage:
                coverage[key].append((typ, ref[-6:]))
        state = 'SUPPRESSED (all tiers off)' if not tiers else \
                'ON: ' + ', '.join(f'{a}/{b}' for a, b in tiers)
        print(f"   [{str(typ):<16}] {name} (op {op}) ref…{ref[-6:]}")
        print(f"        -> {state}")

    print('   --- tier coverage ---')
    for c in COMBOS:
        got = coverage[c]
        if not got:
            msg = (f"ROW {order}: {c[0]}/{c[1]} has NOTHING ENABLED "
                   f"(factory suppressed, no replacement) -> line renders blank")
            print(f"   {c[0]:<8}/{c[1]:<7} : []  <-- NOTHING ENABLED")
            problems.append(msg)
        else:
            print(f"   {c[0]:<8}/{c[1]:<7} : {got}")

print('\n' + '=' * 78)
if problems:
    print(f'FOUND {len(problems)} PROBLEM(S):')
    for p in problems:
        print('  * ' + p)
else:
    print('No tier-coverage gaps and no baseSystemInterval mismatches found.')
    print('If items are still missing, suspect ROW SCOPE (check 3): confirm the')
    print("complaint vehicle's decoded trim actually matches an intended row.")
