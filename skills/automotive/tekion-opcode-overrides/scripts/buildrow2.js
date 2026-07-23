// __buildRow2 — improved row builder for Tekion overrides (2026-06-10)
// Requires override-helpers.js injected first (__fire, __setVal, __commitOpt,
// __openCell, __findSelectRow, __findModelRow, __makeInput).
// Improvements over __buildRow:
//  - polls for slow-loading dropdowns instead of fixed sleeps
//  - scrolls the virtualized year menu to collect ALL options
//  - picks requested∩available years; ERR:no-years-available if none
//  - bails before trim/part if years empty (no stray modal errors)
window.__buildRow2 = async function (o) {
  const S = ms => new Promise(r => setTimeout(r, ms));
  const F = window.__fire, SV = window.__setVal, C = window.__commitOpt, OC = window.__openCell;
  const L = [];
  const mkrx = new RegExp(o.make);
  const mrx = new RegExp('^' + o.modelExact.replace(/[-/().]/g, m => '\\' + m) + '$');

  // 1. MAKE
  const mi = window.__makeInput();
  if (!mi) { L.push('ERR:no-make-input'); return L; }
  mi.scrollIntoView({ block: 'center' });
  SV(mi, o.make);
  let makePicked = null;
  for (let i = 0; i < 8; i++) {
    await S(1200);
    makePicked = C(new RegExp('^' + o.make + '$'));
    if (makePicked) break;
  }
  L.push('make=' + makePicked);
  if (!makePicked) { L.push('ERR:make-not-found'); return L; }
  await S(2200);

  // 2. MODEL
  let row = window.__findSelectRow(mkrx);
  if (!row) { L.push('ERR:no-select-row'); return L; }
  OC(row, 3);
  let modelPicked = null;
  for (let i = 0; i < 8; i++) {
    await S(1200);
    modelPicked = C(mrx);
    if (modelPicked) break;
  }
  L.push('model=' + modelPicked);
  if (!modelPicked) { L.push('ERR:model-not-found'); return L; }
  // Force-close the model dropdown — for some makes (Scion) it stays open and
  // contaminates the cell text, breaking row matching downstream.
  document.body.click();
  await S(1000);
  document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
  await S(1200);

  // Tolerant model-cell matcher: exact match OR open-dropdown leftover
  // ("FR-SAllFR-SiAiM..." starts with model + "All").
  const modelMatches = (td) => {
    const t = window.__modelText(td);
    return t === o.modelExact || t.indexOf(o.modelExact + 'All') === 0;
  };
  const findModelRowT = (yearSel) => {
    for (const tr of document.querySelectorAll('.rt-tr')) {
      const c = tr.querySelectorAll('.rt-td');
      if (c.length < 5) continue;
      if (!mkrx.test(c[2]?.textContent || '')) continue;
      if (!modelMatches(c[3])) continue;
      if (yearSel && !/Select/i.test(c[4]?.textContent || '')) continue;
      return tr;
    }
    return null;
  };

  // 3. YEARS — poll for menu (generic selector), scroll virtualized list, pick intersection
  row = findModelRowT(true);
  if (!row) { L.push('ERR:no-model-row'); return L; }
  OC(row, 4);
  const findMenu = () => {
    // react-select menus have a class ending in "-menu"; fall back to legacy css-11unzgr
    for (const el of document.querySelectorAll('[class*="-menu"], .css-11unzgr')) {
      if (el.offsetParent && el.querySelectorAll('[id*="-option-"]').length) return el;
    }
    return null;
  };
  let menu = null;
  for (let i = 0; i < 12; i++) {
    await S(1200);
    menu = findMenu();
    if (menu) break;
  }
  if (!menu) { L.push('ERR:no-year-menu'); return L; }
  // the scrollable listbox is the child with overflow, or the menu itself
  const scrollEl = () => {
    const m = findMenu();
    if (!m) return null;
    for (const ch of m.querySelectorAll('*')) {
      if (ch.scrollHeight > ch.clientHeight + 5) return ch;
    }
    return m;
  };
  const seen = new Set(), picked = new Set();
  for (let pass = 0; pass < 40; pass++) {
    const m = findMenu();
    if (!m) break;
    let newSeen = false;
    m.querySelectorAll('[id*="-option-"]').forEach(e => {
      const t = (e.textContent || '').trim();
      if (!seen.has(t)) { seen.add(t); newSeen = true; }
      if (o.years.includes(t) && !picked.has(t)) { F(e); picked.add(t); }
    });
    if (picked.size >= o.years.length) break;
    const se = scrollEl();
    if (!se) break;
    const before = se.scrollTop;
    se.scrollTop = before + se.clientHeight;
    await S(600);
    if (se.scrollTop === before && !newSeen) break;
  }
  L.push('avail=' + [...seen].join(','));
  L.push('picked=' + [...picked].join(','));
  document.body.click();
  await S(1500);
  if (picked.size === 0) { L.push('ERR:no-years-available'); return L; }

  // Row finder that targets OUR new row: model matches AND year cell contains
  // a picked year AND (trim blank when wantBlankTrim). Handles duplicate models.
  const pickedArr = [...picked];
  const findOurRow = (wantBlankTrim) => {
    let fallback = null;
    for (const tr of document.querySelectorAll('.rt-tr')) {
      const c = tr.querySelectorAll('.rt-td');
      if (c.length < 6) continue;
      if (!mkrx.test(c[2]?.textContent || '')) continue;
      if (!modelMatches(c[3])) continue;
      const yt = (c[4]?.textContent || '');
      if (!pickedArr.some(y => yt.includes(y))) continue;
      const ti = c[5].querySelector('input');
      const trimBlank = !ti || !ti.value;
      if (wantBlankTrim && !trimBlank) { fallback = fallback || tr; continue; }
      return tr;
    }
    return fallback;
  };

  // 4. TRIM — open modal, All trims radio, modal Save (retry once if blank)
  let trimOk = false;
  for (let attempt = 0; attempt < 2 && !trimOk; attempt++) {
    row = findOurRow(true);
    if (!row) {
      // maybe trim already set from a prior attempt
      row = findOurRow(false);
      if (row) {
        const ti0 = row.querySelectorAll('.rt-td')[5].querySelector('input');
        if (ti0 && ti0.value) { trimOk = true; break; }
      }
      L.push('ERR:row-lost-after-years'); return L;
    }
    const c = row.querySelectorAll('.rt-td');
    const ti = c[5].querySelector('input');
    if (!ti) { L.push('ERR:no-trim-input'); return L; }
    if (ti.value) { trimOk = true; break; }
    const wr = ti.closest('.ant-input-affix-wrapper') || ti.parentElement;
    wr.scrollIntoView({ block: 'center' });
    F(wr);
    let md = null;
    for (let i = 0; i < 8; i++) {
      await S(1000);
      md = document.querySelector('.ant-modal-centered .ant-modal') || document.querySelector('.ant-modal');
      if (md && md.offsetParent !== null) break;
      md = null;
    }
    if (!md) { if (attempt === 0) { await S(2000); continue; } L.push('ERR:no-trim-modal'); return L; }
    const aR = [...md.querySelectorAll('.ant-radio-wrapper')].find(x => /All trims/i.test(x.textContent));
    if (aR) { F(aR); const ri = aR.querySelector('input'); if (ri) ri.click(); }
    await S(800);
    F([...md.querySelectorAll('button')].find(b => b.textContent && b.textContent.trim() === 'Save'));
    await S(2300);
    // verify
    const r2 = findOurRow(false);
    if (r2) {
      const ti2 = r2.querySelectorAll('.rt-td')[5].querySelector('input');
      if (ti2 && ti2.value) trimOk = true;
    }
  }
  if (!trimOk) { L.push('ERR:trim-not-set'); return L; }
  L.push('trim=set');

  // 5. EXPAND + PART
  row = findOurRow(false);
  if (!row) { L.push('ERR:row-lost-after-trim'); return L; }
  const ex = row.querySelector('[data-test-id$="-expanderIcon"]') || row.querySelector('.rt-expandable');
  ex.scrollIntoView({ block: 'center' });
  F(ex);
  let pin = null;
  for (let i = 0; i < 8; i++) {
    await S(1200);
    pin = document.querySelector('[id="@tekion-repairOrders-opcodeManagementV2-customPartsTableCols-customPartsMenuActionId"]');
    if (pin) break;
  }
  if (!pin) { L.push('ERR:no-part-input'); return L; }
  pin.scrollIntoView({ block: 'center' });
  SV(pin, o.part);
  let pm = null;
  for (let i = 0; i < 8; i++) {
    await S(1500);
    pm = C(new RegExp('^' + o.part.replace(/[-]/g, '\\-') + ' - '));
    if (pm) break;
  }
  L.push('part=' + pm);
  if (!pm) { L.push('ERR:part-not-found'); return L; }
  await S(900);

  // 6. PRICE
  const pr = document.querySelector('#customerPayUnitPrice_undefined');
  if (!pr) { L.push('ERR:no-price-input'); return L; }
  pr.focus();
  const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  s.call(pr, o.price);
  ['input', 'change', 'blur'].forEach(t => pr.dispatchEvent(new Event(t, { bubbles: true })));
  L.push('price=' + pr.value);
  return L;
};
