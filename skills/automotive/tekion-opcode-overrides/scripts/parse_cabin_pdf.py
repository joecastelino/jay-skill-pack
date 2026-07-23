#!/usr/bin/env python3
"""
Parse Toyota/Scion Cabin Air Filter PDF into JSON model list.
Output: list of {make, model, part, years, year_label, engines}

Usage: python3 parse_cabin_pdf.py [pdf_path] [--output models.json]
"""
import fitz, json, re, sys, os
from collections import defaultdict

def parse(pdf_path):
    doc = fitz.open(pdf_path)
    raw = ""
    for pg in doc:
        raw += pg.get_text("text")
    doc.close()
    
    lines = raw.split('\n')
    
    # Collect data fields: lines with trailing tab, ignoring headers
    data_fields = []
    for line in lines:
        stripped = line.strip()
        if not stripped: continue
        if line.startswith('\t'): continue  # Header/legend lines
        if '\t' in line:
            value = line.split('\t')[0].strip()
            if value: data_fields.append(value)
        elif re.match(r'^(CH|EE|P|M)$', stripped): data_fields.append(stripped)
        elif re.match(r'^\d{5}', stripped): data_fields.append(stripped)
        elif '---' in stripped: data_fields.append('----------')
    
    # Find 8-field rows by detecting year-range starts
    rows = []
    i = 0
    while i < len(data_fields) - 7:
        if re.match(r'^\d{4}-', data_fields[i]):
            rows.append(data_fields[i:i+8])
            i += 8
        else:
            i += 1
    
    # Known model sequence in PDF order
    model_sequence = [
        ('Toyota', '4Runner'), ('Toyota', 'GR86'),
        ('Toyota', 'Avalon'), ('Toyota', 'bZ4X'),
        ('Toyota', 'C-HR'), ('Toyota', 'Camry'),
        ('Toyota', 'Celica'), ('Toyota', 'Corolla'),
        ('Toyota', 'Corolla Cross'), ('Toyota', 'Corolla Hatchback'),
        ('Toyota', 'Corolla iM'), ('Toyota', 'Crown'),
        ('Toyota', 'Echo'), ('Toyota', 'FJ Cruiser'),
        ('Toyota', 'GR Corolla'), ('Toyota', 'Grand Highlander'),
        ('Toyota', 'Highlander'), ('Toyota', 'Land Cruiser'),
        ('Toyota', 'Matrix'), ('Toyota', 'Mirai'),
        ('Toyota', 'Prius'), ('Toyota', 'Prius c'),
        ('Toyota', 'Prius Plug-In'), ('Toyota', 'Prius v'),
        ('Toyota', 'Prius Prime'), ('Toyota', 'RAV4'),
        ('Toyota', 'RAV4 EV'), ('Toyota', 'RAV4 Prime'),
        ('Toyota', 'Sequoia'), ('Toyota', 'Sienna'),
        ('Toyota', 'Solara'), ('Toyota', 'Supra'),
        ('Toyota', 'Tacoma'), ('Toyota', 'Tundra'),
        ('Toyota', 'Venza'), ('Toyota', 'Yaris'),
        ('Toyota', 'Yaris iA'),
        ('Scion', 'FR-S'), ('Scion', 'iA'),
        ('Scion', 'iM'), ('Scion', 'iQ'),
        ('Scion', 'tC'), ('Scion', 'xA'),
        ('Scion', 'xB'), ('Scion', 'xD'),
    ]
    
    # Parse rows
    raw_entries = []
    for row in rows:
        yr_text, engine = row[0], (row[1] if len(row) > 1 else "")
        
        parts = []
        for cell in row[2:]:
            m = re.search(r'(\d{5}[-]\w{3,})', cell)
            if m: parts.append(m.group(1))
        if not parts: continue
        
        oe, std, prem = parts[0], (parts[1] if len(parts) >= 2 else None), (parts[2] if len(parts) >= 3 else None)
        chosen = std if (std and std != oe) else (prem or oe)
        if not chosen: continue
        
        yr_m = re.match(r'(\d{4})-(\d{4})?', yr_text)
        if not yr_m: continue
        
        raw_entries.append({
            'year_start': int(yr_m.group(1)),
            'year_end': int(yr_m.group(2)) if yr_m.group(2) else 2026,
            'engines': engine, 'part': chosen,
        })
    
    # Map to models using year-reset detection
    entries_out = []
    model_idx = 0
    prev_yr = None
    
    for e in raw_entries:
        yr = e['year_start']
        if prev_yr is not None and yr < prev_yr - 3 and model_idx + 1 < len(model_sequence):
            model_idx += 1
        if model_idx < len(model_sequence):
            make, model = model_sequence[model_idx]
            entries_out.append({
                'make': make, 'model': model,
                'year_start': yr, 'year_end': e['year_end'],
                'engines': e['engines'], 'part': e['part'],
            })
        prev_yr = yr
    
    # Consolidate
    groups = defaultdict(list)
    for e in entries_out:
        groups[(e['make'], e['model'], e['part'])].append(e)
    
    consolidated = []
    for (make, model, part), grp in sorted(groups.items()):
        yr_start = min(g['year_start'] for g in grp)
        yr_end = max(g['year_end'] for g in grp)
        engines = sorted(set(g['engines'] for g in grp))
        years = [str(y) for y in range(yr_start, yr_end + 1)]
        consolidated.append({
            'make': make, 'model': model, 'part': part,
            'years': years, 'year_label': f"{yr_start}-{yr_end}",
            'engines': ', '.join(engines),
            'row_count': len(grp),
        })
    
    # Filter: skip Supra (OE-only), tC (can't retrofit), single-year entries
    consolidated = [c for c in consolidated if c['model'] not in ('Supra', 'tC')]
    consolidated = [c for c in consolidated if len(c['years']) >= 2]
    
    # Sort by make, model
    consolidated.sort(key=lambda c: (c['make'], c['model'], c['year_label']))
    
    return consolidated


if __name__ == '__main__':
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
        "~/.hermes/profiles/jay/cache/documents/doc_83497ac04886_05_CabinAirFilters2024_hi.pdf")
    
    output = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__) or '.', 'models.json')
    
    result = parse(pdf_path)
    with open(output, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Parsed {len(result)} rows across {len(set(r['model'] for r in result))} models -> {output}")
