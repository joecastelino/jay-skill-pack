#!/usr/bin/env python3
"""Build the full CABIN override dataset for Blackstone Toyota from the 2024
Toyota Cabin Air Filter FMPC PDF. Part priority: Standard -> Premium -> OE.
Maps PDF model groups to exact Tekion model-dropdown names (verified 2026-06-10).
Output: /tmp/cabin_bt_full.json
"""
import json

MAX_YEAR = 2026

# (make, [tekion_models], start, end_or_None, part, note)
ENTRIES = [
    # 4Runner — existing rows cover 2003-2009 (wrong part, fix later) + 2010-2026
    ("Toyota", ["4Runner"], 2003, 2009, "87139-YZZ81", "std"),
    ("Toyota", ["4Runner"], 2010, None, "87139-YZZ82", "std"),
    # 86 / GR86 — OE only
    ("Toyota", ["86"], 2017, 2020, "88568-37020", "OE"),
    ("Toyota", ["GR86"], 2022, None, "88568-37020", "OE"),
    # Avalon / Avalon Hybrid
    ("Toyota", ["Avalon", "Avalon Hybrid"], 2000, 2004, "87139-YZZ81", "std"),
    ("Toyota", ["Avalon", "Avalon Hybrid"], 2005, 2018, "87139-YZZ82", "std"),
    ("Toyota", ["Avalon", "Avalon Hybrid"], 2019, None, "87139-YZZ93", "prem"),
    # bZ4X / bZ — OE only (pollen)
    ("Toyota", ["bZ4X", "bZ"], 2023, None, "87139-42040", "OE"),
    # C-HR
    ("Toyota", ["C-HR"], 2018, 2018, "87139-F4010", "OE"),
    ("Toyota", ["C-HR"], 2019, 2022, "87139-YZZ83", "std"),
    # Camry / Camry Hybrid
    ("Toyota", ["Camry", "Camry Hybrid"], 2002, 2006, "87139-YZZ81", "std"),
    ("Toyota", ["Camry", "Camry Hybrid"], 2007, 2017, "87139-YZZ82", "std"),
    ("Toyota", ["Camry", "Camry Hybrid"], 2018, None, "87139-YZZ93", "prem"),
    # Celica
    ("Toyota", ["Celica"], 2000, 2005, "87139-YZZ81", "std"),
    # Corolla family
    ("Toyota", ["Corolla"], 2003, 2008, "87139-YZZ98", "prem"),
    ("Toyota", ["Corolla"], 2009, 2019, "87139-YZZ82", "std"),
    ("Toyota", ["Corolla"], 2020, None, "87139-YZZ83", "std"),
    ("Toyota", ["Corolla Cross"], 2022, None, "87139-YZZ83", "std"),
    ("Toyota", ["Corolla Hatchback"], 2019, None, "87139-YZZ83", "std"),
    ("Toyota", ["Corolla iM"], 2017, 2018, "87139-YZZ82", "std"),
    # GR Corolla — existing row has WRONG part (YZZ92), correct is YZZ83; fix pass handles
    ("Toyota", ["GR Corolla"], 2023, None, "87139-YZZ83", "std"),
    # Crown
    ("Toyota", ["Crown"], 2023, None, "87139-YZZ93", "prem"),
    # Echo
    ("Toyota", ["Echo"], 2000, 2005, "88568-52010-83", "std"),
    # FJ Cruiser
    ("Toyota", ["FJ Cruiser"], 2007, 2014, "87139-YZZ81", "std"),
    # Grand Highlander
    ("Toyota", ["Grand Highlander"], 2024, None, "87139-YZZ83", "std"),
    # Highlander / Highlander Hybrid
    ("Toyota", ["Highlander", "Highlander Hybrid"], 2001, 2007, "87139-48020-83", "std"),
    ("Toyota", ["Highlander", "Highlander Hybrid"], 2008, 2019, "87139-YZZ82", "std"),
    ("Toyota", ["Highlander", "Highlander Hybrid"], 2020, None, "87139-YZZ93", "prem"),
    # Land Cruiser
    ("Toyota", ["Land Cruiser"], 2007, 2007, "88568-60010", "OE"),
    ("Toyota", ["Land Cruiser"], 2008, 2021, "87139-YZZ82", "std"),
    # Matrix
    ("Toyota", ["Matrix"], 2003, 2008, "87139-YZZ98", "prem"),
    ("Toyota", ["Matrix"], 2009, 2013, "87139-YZZ82", "std"),
    # Mirai
    ("Toyota", ["Mirai"], 2016, 2020, "87139-YZZ82", "std"),
    ("Toyota", ["Mirai"], 2021, None, "87139-50110", "OE"),
    # Prius family
    ("Toyota", ["Prius"], 2001, 2009, "87139-YZZ81", "std"),
    ("Toyota", ["Prius"], 2010, 2015, "87139-YZZ82", "std"),
    ("Toyota", ["Prius"], 2016, None, "87139-YZZ83", "std"),
    ("Toyota", ["Prius c"], 2012, 2021, "87139-YZZ82", "std"),
    ("Toyota", ["Prius Plug-In", "Prius Plug-In Hybrid"], 2010, 2015, "87139-YZZ82", "std"),
    ("Toyota", ["Prius v"], 2012, 2017, "87139-YZZ82", "std"),
    ("Toyota", ["Prius Prime"], 2017, None, "87139-YZZ83", "std"),
    # RAV4 family
    ("Toyota", ["RAV4", "RAV4 Hybrid"], 2001, 2005, "88568-52010-83", "std"),
    ("Toyota", ["RAV4", "RAV4 Hybrid"], 2006, 2018, "87139-YZZ82", "std"),
    ("Toyota", ["RAV4", "RAV4 Hybrid"], 2019, None, "87139-YZZ83", "std"),
    ("Toyota", ["RAV4 EV"], 2012, 2014, "87139-YZZ82", "std"),
    ("Toyota", ["RAV4 Prime", "RAV4 Plug-In Hybrid"], 2021, None, "87139-YZZ83", "std"),
    # Sequoia
    ("Toyota", ["Sequoia"], 2008, 2021, "87139-YZZ82", "std"),
    ("Toyota", ["Sequoia"], 2023, None, "87139-YZZA8", "std"),
    # Sienna
    ("Toyota", ["Sienna"], 2004, 2010, "87139-YZZ81", "std"),
    ("Toyota", ["Sienna"], 2011, 2020, "87139-YZZ82", "std"),
    ("Toyota", ["Sienna"], 2021, None, "87139-YZZ93", "prem"),
    # Solara
    ("Toyota", ["Camry Solara"], 2004, 2008, "87139-YZZ81", "std"),
    # Supra (2020+ = GR Supra)
    ("Toyota", ["GR Supra", "Supra"], 2020, None, "87139-WAA01", "OE"),
    # Tacoma
    ("Toyota", ["Tacoma", "Tacoma 2WD", "Tacoma 4WD"], 2005, None, "87139-YZZ09", "std"),
    # Tundra
    ("Toyota", ["Tundra", "Tundra 2WD", "Tundra 4WD"], 2007, 2021, "87139-YZZ82", "std"),
    ("Toyota", ["Tundra", "Tundra 2WD", "Tundra 4WD"], 2022, None, "87139-YZZA8", "std"),
    ("Toyota", ["Tundra Hybrid 2WD", "Tundra Hybrid 4WD"], 2022, None, "87139-YZZA8", "std"),
    # Venza
    ("Toyota", ["Venza"], 2009, 2016, "87139-YZZ82", "std"),
    ("Toyota", ["Venza"], 2021, None, "87139-YZZ83", "std"),
    # Yaris family
    ("Toyota", ["Yaris"], 2006, 2016, "87139-YZZ82", "std"),
    ("Toyota", ["Yaris iA"], 2017, 2020, "87139-WB001", "OE"),
    ("Toyota", ["Yaris Sedan"], 2017, 2020, "87139-WB001", "OE"),
    ("Toyota", ["Yaris Hatchback"], 2020, 2020, "87139-WB001", "OE"),
    # Scion (separate make in Tekion)
    ("Scion", ["FR-S"], 2013, 2016, "88568-37020", "OE"),
    ("Scion", ["iA"], 2016, 2016, "87139-WB001", "OE"),
    ("Scion", ["iM"], 2016, 2016, "87139-YZZ82", "std"),
    ("Scion", ["iQ"], 2012, 2015, "88568-74011", "OE"),
    ("Scion", ["tC"], 2009, 2010, "88568-52010-83", "std"),
    ("Scion", ["tC"], 2011, 2016, "87139-YZZ82", "std"),
    ("Scion", ["xA"], 2004, 2006, "88568-52010-83", "std"),
    ("Scion", ["xB"], 2004, 2006, "88568-52010-83", "std"),
    ("Scion", ["xB"], 2008, 2015, "87139-YZZ82", "std"),
    ("Scion", ["xD"], 2008, 2014, "87139-YZZ82", "std"),
]

rows = []
for make, models, start, end, part, note in ENTRIES:
    e = end if end else MAX_YEAR
    years = [str(y) for y in range(start, e + 1)]
    for m in models:
        rows.append({
            "make": make, "model": m, "years": years,
            "year_label": f"{start}-{e}", "part": part, "note": note,
        })

with open("/tmp/cabin_bt_full.json", "w") as f:
    json.dump(rows, f, indent=1)
print(f"{len(rows)} rows across {len(set(r['model'] for r in rows))} models -> /tmp/cabin_bt_full.json")
