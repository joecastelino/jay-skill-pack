// Tekion Opcode Overrides — Helper Toolkit (VERIFIED 2026-06-04)
// Inject this ONCE per session via browser_console. RE-INJECT after every
// reload / about:blank blank-out (helpers are wiped by SPA reload).
//
// After injection, build a row with:
//   window.__buildRow({make:'Toyota', makeRx:/Toyota/, modelExact:'RAV4',
//                       years:['2026','2025',...], part:'87139-YZZ83', price:'30.88'})
// then set TRIM with a REAL browser_click (synthetic clicks no-op — see SKILL.md Rule 1),
// then save with a REAL browser_click on querySelectorAll('#btnSalesSetupSave')[1],
// then RELOAD + verify via the API (tekion-opcode-api).

window.__fire=(el)=>['mousedown','mouseup','click'].forEach(t=>el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})));

window.__setVal=(inp,v)=>{inp.focus();const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(inp,v);inp.dispatchEvent(new Event('input',{bubbles:true}));};

window.__commitOpt=(rx)=>{let hit=null;document.querySelectorAll('[id^="react-select-"][id*="-option-"]').forEach(e=>{if(rx.test((e.textContent||'').trim())&&!hit&&e.offsetParent)hit=e;});if(hit)window.__fire(hit);return hit?(hit.textContent||'').trim():null;};

window.__makeInput=()=>{let b=null;document.querySelectorAll('input[id^="@tekion-repair-orders-opcodeManagementV2-vehicle"]').forEach(i=>{const r=i.getBoundingClientRect();if(r.x>40&&r.x<1300)b=i;});return b;};

window.__modelText=(td)=>(td?.textContent||'').replace(/.*}/,'').replace(/All2WD.*/,'').trim();

window.__openCell=(tr,idx)=>{const c=tr.querySelectorAll('.rt-td');const cell=c[idx];cell.scrollIntoView({block:'center'});window.__fire(cell.querySelector('input,[class*="control"],[class*="selectedValues"]')||cell);};

window.__findSelectRow=(mk)=>{for(const tr of document.querySelectorAll('.rt-tr')){const c=tr.querySelectorAll('.rt-td');if(c.length<5)continue;if(mk.test(c[2]?.textContent||'')&&/Select\.\.\./.test(c[3]?.textContent||''))return tr;}return null;};

window.__findModelRow=(mk,model,yearSel)=>{for(const tr of document.querySelectorAll('.rt-tr')){const c=tr.querySelectorAll('.rt-td');if(c.length<5)continue;if(!mk.test(c[2]?.textContent||''))continue;if(window.__modelText(c[3])!==model)continue;if(yearSel&&!/Select/i.test(c[4]?.textContent||''))continue;return tr;}return null;};

window.__save=()=>{const b=document.querySelectorAll('#btnSalesSetupSave');if(b.length<2)return'no-save';window.__fire(b[1]);return'saved';};

// FULL builder. opts={make, makeRx?, modelExact, modelRx?, years:[...], part, price, dedupeModels?:[]}
// Fills Make->Model->Year->(trim attempted, but DO IT WITH A REAL CLICK)->Part->Price.
window.__buildRow=async function(o){
  const S=ms=>new Promise(r=>setTimeout(r,ms)),F=window.__fire,SV=window.__setVal,C=window.__commitOpt,OC=window.__openCell,L=[];
  const mk=o.makeRx||/Toyota/, mrx=o.modelRx||new RegExp('^'+o.modelExact.replace(/[-/]/g,m=>'\\'+m)+'$');
  const mi=window.__makeInput();mi.scrollIntoView({block:'center'});SV(mi,o.make);await S(2600);L.push('make='+C(new RegExp('^'+o.make+'$')));await S(2500);
  let row=window.__findSelectRow(mk);if(!row){L.push('ERR:no-select-row');return L;}OC(row,3);await S(2300);L.push('model='+C(mrx));await S(1600);
  if(o.dedupeModels&&o.dedupeModels.length){row=window.__findModelRow(mk,o.modelExact);if(row){OC(row,3);await S(1800);for(const dm of o.dedupeModels){let h=null;document.querySelectorAll('[id^="react-select-"][id*="-option-"]').forEach(e=>{if((e.textContent||'').trim()===dm&&e.offsetParent&&!h)h=e;});if(h){const cb=h.querySelector('input[type="checkbox"]');if(cb&&cb.checked){F(h);L.push('dedupe-'+dm);}}}document.body.click();await S(1000);}}
  row=window.__findModelRow(mk,o.modelExact,true);if(!row){L.push('ERR:no-model-row');return L;}OC(row,4);await S(2300);
  const menu=document.querySelector('.css-11unzgr');const avail=menu?[...menu.querySelectorAll('[id*="-option-"]')].map(e=>(e.textContent||'').trim()):[];L.push('avail='+avail.join(','));
  let pk=[];if(menu){menu.querySelectorAll('[id*="-option-"]').forEach(e=>{const t=(e.textContent||'').trim();if(o.years.includes(t)){F(e);pk.push(t);}});}L.push('picked='+pk.join(','));document.body.click();await S(1200);
  row=window.__findModelRow(mk,o.modelExact);const c=row.querySelectorAll('.rt-td');const ti=c[5].querySelector('input[id^="trim_"]');const wr=ti.closest('.ant-input-affix-wrapper')||ti.parentElement;wr.scrollIntoView({block:'center'});F(wr);await S(2300);
  const md=document.querySelector('.ant-modal-centered .ant-modal')||document.querySelector('.ant-modal');if(!md){L.push('ERR:no-modal');return L;}
  // NOTE: this synthetic radio set is UNRELIABLE — verify cell[5]=="All trims selected"
  // after, and if blank, set it with a REAL browser_click (see SKILL.md Rule 1).
  const aR=[...md.querySelectorAll('.ant-radio-wrapper')].find(x=>/All trims/i.test(x.textContent));if(aR){F(aR);const ri=aR.querySelector('input');if(ri)ri.click();}await S(700);
  F([...md.querySelectorAll('button')].find(b=>b.textContent?.trim()==='Save'));L.push('trim=All(attempted)');await S(2300);
  row=window.__findModelRow(mk,o.modelExact);const ex=row.querySelector('[data-test-id$="-expanderIcon"]')||row.querySelector('.rt-expandable');ex.scrollIntoView({block:'center'});F(ex);await S(2300);
  const pin=document.querySelector('[id="@tekion-repairOrders-opcodeManagementV2-customPartsTableCols-customPartsMenuActionId"]');if(!pin){L.push('ERR:no-part-input');return L;}pin.scrollIntoView({block:'center'});SV(pin,o.part);await S(3300);
  const pm=C(new RegExp('^'+o.part.replace(/[-]/g,'\\-')+' - '));L.push('part='+pm);if(!pm){L.push('ERR:part-not-found');return L;}await S(900);
  const pr=document.querySelector('#customerPayUnitPrice_undefined');pr.focus();const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(pr,o.price);['input','change','blur'].forEach(t=>pr.dispatchEvent(new Event(t,{bubbles:true})));L.push('price='+pr.value);return L;
};
