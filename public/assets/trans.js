/* 학습 자료실 '번역 교정' (관리자만) — /study/trans/ 페이지와 학습 자료실 '번역 교정' 탭이 함께 씀 (운영자 요청, 2026-11-28)
   window.ddTrans.mount(그릴 곳, {prefix: 주소 # 앞머리('trans' 면 #trans/자료ID/r123), page: 따로 페이지면 true}) */
(function(){
const CSS_TEXT=".txw .cmpol{white-space:normal;margin:6px 0 10px;border:1px solid var(--line,#ddd);border-radius:8px;padding:6px 12px;background:var(--paper2,#faf7f0)}\n.txw .cmpol summary{cursor:pointer;font-weight:600}\n.txw .cmpol dt{font-weight:600;margin-top:6px}\n.txw .cmpol dd{margin:0 0 0 1em}\n.txw details.cm{white-space:normal;line-height:1.6;margin:6px 0 2px;border-left:3px solid #c59a3c;padding:2px 0 2px 10px;background:rgba(197,154,60,.07)}\n.txw details.cm summary{cursor:pointer;font-size:.9em;font-weight:600}\n.txw details.cm ol{margin:4px 0;padding-left:1.4em}\n.txw details.cm li{margin:6px 0 10px}\n.txw details.cm li.done{opacity:.6}\n.txw .cm-tag{display:inline-block;font-size:.78em;padding:0 6px;border-radius:4px;background:#7E4520;color:#fff}\n.txw .cm-star{color:#b8860b;margin-left:2px}\n.txw .cm-l{display:inline-block;min-width:3.4em;font-size:.8em;color:var(--ink-soft,#666)}\n.txw .cm-a{text-decoration:line-through;text-decoration-color:rgba(160,40,40,.5)}\n.txw .cm-b{color:#1846a3;font-weight:600}\n.txw .cm-why{font-size:.9em;margin-top:2px}\n.txw .cm-en{font-size:.85em;color:var(--ink-soft,#666);font-style:italic}\n.txw .cm-act{margin-top:4px}\n.txw .cm-ok{color:#2b7a2b;font-weight:600}\n.txw .colchip{display:inline-flex;align-items:center;gap:2px;border:1px solid var(--line,#ccc);border-radius:6px;padding:1px 4px;margin:2px 2px}\n.txw .colchip button{padding:0 5px;min-width:0;font-size:.8em;line-height:1.6}\n.txw .colchip button[disabled]{opacity:.3}\n.txw .c.rc{color:var(--ink-soft);font-size:.85em;font-style:italic}\n.txw .txttl{font-size:21px;margin:4px 0 2px}\n.txw .tblw{overflow-x:auto}\n.txw table.txlist{width:100%;border-collapse:collapse;font-size:14.5px}\n.txw table.txlist th,.txw table.txlist td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}\n.txw table.txlist th{font-size:12.5px;color:var(--ink-soft);font-weight:600}\n.txw table.txlist .n{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}\n.txw table.txlist td a{font-weight:600}\n.txw table.txlist tbody tr:hover{background:var(--paper-2)}\n.txw.in-study{padding:0 0 120px;max-width:none}\n.txw{max-width:1400px;margin:0 auto;padding:20px 18px 120px}\n.txw .tr-wrap h1{font-size:24px;margin:10px 0 4px}\n.txw .top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;font-size:14px}\n.txw .note{font-size:13.5px;color:var(--ink-soft);line-height:1.65}\n.txw .card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-top:16px}\n.txw .card h2{font-size:16px;margin:0 0 10px}\n.txw input[type=password],.txw input[type=search],.txw select{height:38px;border:1px solid var(--line);border-radius:8px;padding:0 10px;background:var(--paper);font-size:14.5px;color:var(--ink)}\n.txw .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}\n.txw .msg{border-radius:8px;padding:10px 12px;font-size:14px;margin-top:10px;line-height:1.6}\n.txw .msg.ok{background:var(--leaf-soft);color:var(--leaf)}\n.txw .msg.err{background:#F6E1DC;color:#8A2E1C}\n.txw .docs{list-style:none;padding:0;margin:0}\n.txw .docs li{border-bottom:1px solid var(--line);padding:12px 2px;display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:center}\n.txw .docs a{font-size:16px;font-weight:600}\n.txw .sm{font-size:12.5px;color:var(--ink-soft)}\n.txw button.b{border:1px solid var(--line);background:var(--paper);border-radius:8px;padding:6px 11px;font-size:13.5px;cursor:pointer;color:var(--ink)}\n.txw button.b:hover{border-color:var(--robe)}\n.txw button.b.on{background:var(--robe);border-color:var(--robe);color:var(--paper)}\n.txw button.b.pri{background:var(--robe);border-color:var(--robe);color:var(--paper)}\n.txw .txseg{display:inline-flex;border:1px solid var(--line);border-radius:9px;overflow:hidden}\n.txw .txseg button{border:0;background:var(--paper);padding:7px 13px;font-size:14px;cursor:pointer;color:var(--ink)}\n.txw .txseg button+button{border-left:1px solid var(--line)}\n.txw .txseg button[aria-pressed=true]{background:var(--robe);color:var(--paper)}\n.txw .bar{position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid var(--line);padding:10px 0;margin-top:10px;display:flex;gap:8px 14px;flex-wrap:wrap;align-items:center;font-size:14px}\n.txw .bar label{display:inline-flex;gap:5px;align-items:center;cursor:pointer}\n.txw .bar .grow{flex:1}\n.txw #status{font-size:13px;color:var(--leaf);min-height:18px}\n.txw #status.err{color:#8A2E1C}\n.txw /* 대조 보기 */\n  .txgrid{margin-top:6px}\n.txw .hdr,.txw .tr{display:grid;gap:14px;grid-template-columns:var(--cols)}\n.txw .hdr{font-size:12.5px;color:var(--ink-soft);font-weight:600;padding:8px 10px;border-bottom:2px solid var(--line)}\n.txw .tr{padding:10px 10px;border-bottom:1px solid var(--line);line-height:1.75;font-size:calc(15px*var(--fz,1))}\n.txw .tr.h{font-weight:700}\n.txw .tr.cur{background:var(--robe-soft)}\n.txw .tr .c{min-width:0;white-space:pre-wrap;word-break:keep-all;overflow-wrap:anywhere}\n.txw .tr .c.o{font-family:var(--serif);color:var(--ink)}\n.txw .tr .c.r{color:var(--ink-soft)}\n.txw .tr .c.t{cursor:text;border-radius:6px;padding:2px 6px;margin:-2px -6px;outline:1px dashed transparent}\n.txw .tr .c.t:hover{outline-color:var(--line)}\n.txw .tr .c.t:focus-visible{outline:2px solid var(--robe)}\n.txw .tr .c.t.empty{color:var(--ink-soft);font-style:italic}\n.txw .tr.edited .c.t{background:var(--leaf-soft)}\n.txw .tr .meta{grid-column:1/-1;display:flex;gap:10px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--ink-soft);margin-top:-2px}\n.txw .tr .meta button{font-size:12px;border:0;background:none;color:var(--robe);cursor:pointer;padding:0;text-decoration:underline}\n.txw .tr .meta .tag{background:var(--leaf-soft);color:var(--leaf);border-radius:5px;padding:0 6px}\n.txw .tr .meta .tag.only{background:var(--paper-2);color:var(--ink-soft)}\n.txw .tr textarea{width:100%;min-height:60px;font:inherit;font-weight:400;line-height:1.75;border:2px solid var(--robe);border-radius:8px;padding:6px 8px;background:var(--card);color:var(--ink);resize:vertical}\n.txw .ed-acts{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap;align-items:center}\n.txw .box{grid-column:1/-1;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:13.5px}\n.txw .box ol{margin:4px 0 0;padding-left:20px}\n.txw .box li{margin:6px 0;white-space:pre-wrap}\n.txw .box textarea{min-height:50px}\n.txw .note-show{grid-column:1/-1;font-size:13px;background:#FFF6D8;color:#5B4A12;border-radius:6px;padding:6px 10px;white-space:pre-wrap}\n.txw /* 번역본만 */\n  .txreader{max-width:780px;margin:22px auto 0;font-size:calc(17px*var(--fz,1));line-height:1.95}\n.txw .txreader p{margin:0 0 1em;text-indent:1em;word-break:keep-all}\n.txw .txreader p.h{text-indent:0;font-weight:700;margin-top:1.6em}\n.txw .txreader span.s{cursor:pointer;border-radius:4px}\n.txw .txreader span.s:hover{background:var(--robe-soft)}\n.txw .txreader.marks span.s.ed{background:var(--leaf-soft)}\n.txw .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}\n@media (max-width:760px){.txw .hdr{display:none}\n.txw .bar{position:static}\n.txw .hdr,.txw .tr{grid-template-columns:1fr !important}\n.txw .tr .c::before{content:attr(data-l);display:block;font-size:11.5px;color:var(--ink-soft);font-weight:600;font-family:var(--sans)}}";
function mount(ROOT,OPT){
OPT=OPT||{}; if(ROOT._tx) return; ROOT._tx=1;
if(!document.getElementById('txCss')){ const st=document.createElement('style'); st.id='txCss'; st.textContent=CSS_TEXT; document.head.appendChild(st); }
ROOT.classList.add('txw'); ROOT.innerHTML="<div class=\"card\" id=\"tokCard\" hidden>\n    <h2>관리자 열쇠</h2>\n    <p class=\"note\">번역 교정은 관리자만 쓸 수 있습니다. 관리자 화면에 로그인할 때 쓴 GitHub 열쇠(github_pat_…)를 한 번 넣어 주세요. 이 브라우저에만 저장됩니다.</p>\n    <div class=\"row\"><label for=\"tok\" class=\"sr\">관리자 열쇠</label><input type=\"password\" id=\"tok\" name=\"dd-admin-key\" placeholder=\"github_pat_…\" autocomplete=\"new-password\" data-lpignore=\"true\" style=\"flex:1\"><button class=\"b pri\" id=\"tokSave\">확인</button></div>\n    <div id=\"tokMsg\" role=\"status\"></div>\n  </div>\n\n  <div id=\"listView\" hidden>\n    <p class=\"note\">원서 문장, 대조 번역본, 우리 번역을 문장마다 나란히 놓고 우리 번역을 바로 고치는 곳입니다. 고친 글은 비공개 창고에만 저장되고, 고치기 전 글은 기록으로 남아 언제든 되돌릴 수 있습니다.</p>\n    <div class=\"card\"><h2>번역 교정 목록</h2><div class=\"tblw\"><table class=\"txlist\"><thead><tr><th>자료</th><th class=\"n\">줄</th><th class=\"n\">고친 줄</th><th class=\"n\">메모</th><th class=\"n\">교정 의견</th><th>마지막 저장</th></tr></thead><tbody id=\"docs\"><tr><td colspan=\"6\" class=\"sm\">불러오는 중…</td></tr></tbody></table></div></div>\n    <div class=\"card\">\n      <h2>새 자료 넣기</h2>\n      <p class=\"note\">Claude 가 만들어 드린 자료 파일(<b>….trans.json</b>)이나 대조 번역본 파일(<b>….ref.json</b>)을 골라 주세요. 대조 번역본은 이미 넣은 자료에 더해지고, 우리 번역·고친 기록·메모는 그대로입니다.</p>\n      <div class=\"row\"><input type=\"file\" id=\"file\" accept=\".json,application/json\"></div>\n      <div id=\"impMsg\" role=\"status\"></div>\n    </div>\n  </div>\n\n  <div id=\"docView\" hidden>\n    <p class=\"sm\" style=\"margin:0 0 6px\"><a href=\"#\" id=\"txBack\">← 번역 교정 목록</a></p>\n    <h2 class=\"txttl\" id=\"ttl\"></h2>\n    <p class=\"sm\" id=\"docInfo\"></p>\n    <details class=\"cmpol\" id=\"cmPol\" hidden></details>\n    <div class=\"bar\" role=\"toolbar\" aria-label=\"보기 설정\">\n      <div class=\"txseg\" role=\"group\" aria-label=\"보기\">\n        <button type=\"button\" id=\"vCmp\" aria-pressed=\"true\">대조 보기</button>\n        <button type=\"button\" id=\"vRead\" aria-pressed=\"false\">번역본만</button>\n      </div>\n      <span id=\"colToggles\"></span>\n      <label><input type=\"checkbox\" id=\"fEdited\"> 고친 줄만</label>\n      <label><input type=\"checkbox\" id=\"fNote\"> 메모 있는 줄만</label>\n      <label class=\"cmopt\" hidden><input type=\"checkbox\" id=\"fCm\"> 교정 의견 남은 줄만</label>\n      <label class=\"cmopt\" hidden><input type=\"checkbox\" id=\"fCmOpen\"> 교정 의견 펼쳐 보기</label>\n      <label class=\"rdOnly\" style=\"display:none\"><input type=\"checkbox\" id=\"fMarks\"> 고친 문장 표시</label>\n      <label><span class=\"sr\">찾기</span><input type=\"search\" id=\"q\" autocomplete=\"off\" placeholder=\"찾기 (모든 칸)\" style=\"width:170px\"></label>\n      <span class=\"sm\" id=\"cnt\"></span>\n      <span class=\"grow\"></span>\n      <button class=\"b\" id=\"fzDn\" aria-label=\"글자 작게\">가−</button><button class=\"b\" id=\"fzUp\" aria-label=\"글자 크게\">가+</button>\n      <button class=\"b\" id=\"dlTxt\">번역본 내려받기</button>\n      <button class=\"b\" id=\"dlCsv\">대조표 내려받기</button>\n    </div>\n    <div id=\"status\" role=\"status\" aria-live=\"polite\"></div>\n    <div id=\"cmp\"><div class=\"txgrid\"><div class=\"hdr\" id=\"hdr\"></div><div id=\"rows\"></div></div></div>\n    <div id=\"read\" hidden><div class=\"txreader\" id=\"reader\"></div></div>\n  </div>\n";
const P=OPT.prefix||'';
function parseHash(){ const h=decodeURIComponent(location.hash.slice(1)); const p=h.split('/'); if(P){ if(p[0]!==P) return null; p.shift(); } return [p[0]||'',p[1]||'']; }
function hashFor(id,row){ return '#'+[P,id,row].filter(Boolean).join('/'); }
const rowEl=id=>ROOT.querySelector('#tx-'+CSS.escape(id));

const REPO='dhammapiya3-lab/dhammadana';
const $=s=>ROOT.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let TOKEN='', DOC=null, BY={}, VIEW='cmp', EDITING=null, QUEUE=Promise.resolve(), PENDING=0;
const LS={get(k,d){try{const v=localStorage.getItem(k);return v==null?d:JSON.parse(v)}catch(e){return d}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
try{ localStorage.setItem('dd-notrack','true'); }catch(e){}

function findToken(){
  try{ const t=localStorage.getItem('dd-gh-token'); if(t) return t; }catch(e){}
  try{ for(let i=0;i<localStorage.length;i++){ const k=localStorage.key(i); if(!/sveltia/i.test(k)) continue;
    const v=localStorage.getItem(k); const m=v&&v.match(/"token"\s*:\s*"([^"]+)"/); if(m) return m[1]; } }catch(e){}
  return '';
}
async function check(t){
  try{ const r=await fetch('https://api.github.com/repos/'+REPO,{headers:{authorization:'Bearer '+t,accept:'application/vnd.github+json'}});
    if(!r.ok) return false; const j=await r.json(); return !!(j.permissions&&(j.permissions.push||j.permissions.admin)); }catch(e){ return false; }
}
const api=(q='',opt={})=>fetch('/api/trans'+q,{...opt,cache:'no-store',headers:{authorization:'Bearer '+TOKEN,...(opt.headers||{})}});
async function start(){
  TOKEN=findToken();
  if(TOKEN && await check(TOKEN)) route(); else $('#tokCard').hidden=false;
}
$('#tokSave').onclick=async()=>{
  const t=$('#tok').value.trim(); $('#tokMsg').innerHTML='<p class="note">확인 중…</p>';
  if(await check(t)){ TOKEN=t; try{localStorage.setItem('dd-gh-token',t)}catch(e){} $('#tokCard').hidden=true; route(); }
  else $('#tokMsg').innerHTML='<div class="msg err">이 열쇠로는 들어갈 수 없습니다. 열쇠가 맞는지, 기한이 지나지 않았는지 확인해 주세요.</div>';
};
const say=(m,err)=>{ const s=$('#status'); s.textContent=m; s.className=err?'err':''; };
const day=d=>{ const x=new Date(d); return isNaN(x)?'':`${x.getFullYear()}.${x.getMonth()+1}.${x.getDate()} ${String(x.getHours()).padStart(2,'0')}:${String(x.getMinutes()).padStart(2,'0')}`; };

// ---------- 주소: #자료ID 또는 #자료ID/r123 ----------
function route(){
  const hp=parseHash(); if(!hp) return; const [id,row]=hp;
  if(!id){ $('#docView').hidden=true; $('#listView').hidden=false;  if(OPT.page) document.title='번역 교정 · 학습 자료실 (관리자)'; loadList(); return; }
  if(DOC&&DOC.id===id){ $('#listView').hidden=true; $('#docView').hidden=false; if(row) goRow(row); return; }
  loadDoc(id,row);
}
addEventListener('hashchange',route); $('#txBack').onclick=e=>{ e.preventDefault(); location.hash=hashFor(); if(!P) route(); };

async function loadList(){
  try{ const r=await api(); const j=await r.json(); if(!r.ok) throw new Error(j.error||r.status);
    const it=j.items||[];
    $('#docs').innerHTML=it.length?it.map(d=>`<tr><td><a href="${esc(hashFor(d.id))}">${esc(d.title)}</a></td><td class="n">${d.rows}</td><td class="n">${d.edited}</td><td class="n">${d.notes||0}</td><td class="n">${d.cm?(d.cmDone||0)+' / '+d.cm:''}</td><td class="sm">${esc(day(d.updated))}</td></tr>`).join(''):'<tr><td colspan="5" class="sm">아직 넣은 자료가 없습니다. 아래에서 자료 파일을 넣어 주세요.</td></tr>';
  }catch(e){ $('#docs').innerHTML=`<tr><td colspan="5"><div class="msg err">목록을 불러오지 못했습니다: ${esc(e.message)}</div></td></tr>`; }
}
$('#file').onchange=async e=>{
  const f=e.target.files[0]; if(!f) return; let d;
  try{ d=JSON.parse(await f.text()); }catch(x){ $('#impMsg').innerHTML='<div class="msg err">자료 파일을 읽지 못했습니다. Claude 가 만든 ….trans.json 파일인지 확인해 주세요.</div>'; return; }
  if(d&&d.kind==='ref') await importRef(d,false); else if(d&&d.kind==='cm') await importCm(d,false); else await importDoc(d,false);
};
// 대조 번역본만 넣기 — 우리 번역·고친 기록·메모는 그대로 (2026-11-28)
async function importRef(d,replace){
  $('#impMsg').innerHTML='<p class="note">대조 번역본을 넣는 중…</p>';
  const r=await api('?id='+encodeURIComponent(d.id||'')+'&ref=1'+(replace?'&replace=1':''),{method:'PUT',headers:{'content-type':'application/json'},body:JSON.stringify(d)});
  const j=await r.json().catch(()=>({}));
  if(r.status===409){ $('#impMsg').innerHTML=`<div class="msg err">‘${esc(d.title||d.id)}’ 자료에 이미 대조 번역본이 있습니다. 새 대조 번역본으로 바꿀까요? (우리 번역·고친 기록·메모는 그대로입니다)<div class="row"><button class="b" id="impNo">그대로 두기</button><button class="b" id="impYes">새 대조 번역본으로 바꾸기</button></div></div>`;
    $('#impNo').onclick=()=>{ $('#impMsg').innerHTML=''; $('#file').value=''; }; $('#impYes').onclick=()=>importRef(d,true); return; }
  if(!r.ok){ $('#impMsg').innerHTML=`<div class="msg err">넣지 못했습니다: ${esc(j.error||r.status)}</div>`; return; }
  $('#impMsg').innerHTML=`<div class="msg ok">‘${esc(j.title||d.id)}’ 자료에 대조 번역본을 넣었습니다 (${j.ref}줄${j.miss?`, 맞는 줄이 없는 것 ${j.miss}`:''}). 우리 번역과 고친 기록은 그대로입니다.</div>`; $('#file').value=''; DOC=null; loadList();
}
// 교정 의견만 넣기 — 우리 번역·고친 기록·메모는 그대로 (2026-11-28)
async function importCm(d,replace){
  $('#impMsg').innerHTML='<p class="note">교정 의견을 넣는 중…</p>';
  const r=await api('?id='+encodeURIComponent(d.id||'')+'&cm=1'+(replace?'&replace=1':''),{method:'PUT',headers:{'content-type':'application/json'},body:JSON.stringify(d)});
  const j=await r.json().catch(()=>({}));
  if(r.status===409){ $('#impMsg').innerHTML=`<div class="msg err">이 자료에 이미 교정 의견이 있습니다. 새 교정 의견으로 바꿀까요? (우리 번역·고친 기록·메모는 그대로입니다)<div class="row"><button class="b" id="impNo">그대로 두기</button><button class="b" id="impYes">새 교정 의견으로 바꾸기</button></div></div>`;
    $('#impNo').onclick=()=>{ $('#impMsg').innerHTML=''; $('#file').value=''; }; $('#impYes').onclick=()=>importCm(d,true); return; }
  if(!r.ok){ $('#impMsg').innerHTML=`<div class="msg err">넣지 못했습니다: ${esc(j.error||r.status)}</div>`; return; }
  $('#impMsg').innerHTML=`<div class="msg ok">‘${esc(j.title||d.id)}’ 자료에 교정 의견 ${j.cmAdded}개를 넣었습니다${j.miss?` (맞는 줄이 없는 것 ${j.miss})`:''}. 우리 번역과 고친 기록은 그대로입니다.</div>`; $('#file').value=''; DOC=null; loadList();
}
async function importDoc(d,replace){
  $('#impMsg').innerHTML='<p class="note">넣는 중…</p>';
  const r=await api('?id='+encodeURIComponent(d.id||'')+(replace?'&replace=1':''),{method:'PUT',headers:{'content-type':'application/json'},body:JSON.stringify(d)});
  const j=await r.json().catch(()=>({}));
  if(r.status===409){ $('#impMsg').innerHTML=`<div class="msg err">‘${esc(d.title)}’ 자료가 이미 있습니다. 새 파일로 바꾸면 <b>지금까지 고친 글과 기록이 모두 사라집니다.</b><div class="row"><button class="b" id="impNo">그대로 두기</button><button class="b" id="impYes">새 파일로 바꾸기</button></div></div>`;
    $('#impNo').onclick=()=>{ $('#impMsg').innerHTML=''; $('#file').value=''; }; $('#impYes').onclick=()=>importDoc(d,true); return; }
  if(!r.ok){ $('#impMsg').innerHTML=`<div class="msg err">넣지 못했습니다: ${esc(j.error||r.status)}</div>`; return; }
  $('#impMsg').innerHTML=`<div class="msg ok">‘${esc(d.title)}’ 자료를 넣었습니다 (줄 ${j.rows}).</div>`; $('#file').value=''; loadList();
}

// ---------- 자료 하나 ----------
async function loadDoc(id,row){
  $('#listView').hidden=true; $('#docView').hidden=false; $('#rows').innerHTML='<p class="sm" style="padding:10px">불러오는 중…</p>';
  try{ const r=await api('?id='+encodeURIComponent(id)); const j=await r.json(); if(!r.ok) throw new Error(j.error||r.status); DOC=j; }
  catch(e){ $('#rows').innerHTML=`<div class="msg err">자료를 불러오지 못했습니다: ${esc(e.message)}</div>`; return; }
  BY=Object.fromEntries(DOC.rows.map((r,i)=>[r.id,Object.assign(r,{_i:i})]));
  $('#ttl').textContent=DOC.title; if(OPT.page) document.title=DOC.title+' · 번역 교정';
  $('#docInfo').innerHTML=[DOC.info&&DOC.info.o?`${esc(DOC.cols.o)}: ${esc(DOC.info.o)}`:'',DOC.info&&DOC.info.r?`${esc(DOC.cols.r)}: ${esc(DOC.info.r)}`:'',DOC.info&&DOC.info.t?`${esc(DOC.cols.t)}: ${esc(DOC.info.t)}`:''].filter(Boolean).join('<br>');
  const hasR=DOC.rows.some(r=>r.r);
  const on=LS.get('dd-trans-cols',{o:true,r:true});
  drawToggles();
  cmPolicy();
  ROOT.style.setProperty('--fz',LS.get('dd-trans-fz',1));
  setView(LS.get('dd-trans-view','cmp'),true);
  if(row) setTimeout(()=>goRow(row),50);
}
// 칸 차례: 처음은 원서 | 우리 번역 | 대조 번역본, ◀ ▶ 로 옮겨 이 기기에 기억
function order(){ const hasR=DOC.rows.some(r=>r.r); const all=['o','t',...(hasR?['r']:[])];
  const sv=LS.get('dd-trans-order',null); const o=Array.isArray(sv)?sv.filter(c=>all.includes(c)):[];
  all.forEach(c=>{ if(!o.includes(c)) o.push(c); }); return o; }
function cols(){ const v=LS.get('dd-trans-cols',{}); return order().filter(c=>c==='t'||v[c]!==false); }
function drawToggles(focus){
  const on=LS.get('dd-trans-cols',{}); const od=order();
  $('#colToggles').innerHTML='<span class="sm">칸 차례:</span> '+od.map((c,i)=>`<span class="colchip">${c==='t'?`<b>${esc(DOC.cols.t)}</b>`:`<label><input type="checkbox" data-col="${c}" ${on[c]!==false?'checked':''}> ${esc(DOC.cols[c])}</label>`}<button type="button" data-mv="${c}" data-d="-1" ${i===0?'disabled':''} aria-label="${esc(DOC.cols[c])} 칸을 왼쪽으로">◀</button><button type="button" data-mv="${c}" data-d="1" ${i===od.length-1?'disabled':''} aria-label="${esc(DOC.cols[c])} 칸을 오른쪽으로">▶</button></span>`).join(' ');
  ROOT.querySelectorAll('[data-col]').forEach(c=>c.onchange=()=>{ const v=LS.get('dd-trans-cols',{}); v[c.dataset.col]=c.checked; LS.set('dd-trans-cols',v); drawCmp(); });
  ROOT.querySelectorAll('[data-mv]').forEach(b=>b.onclick=()=>{ const o=order(), i=o.indexOf(b.dataset.mv), j=i+(+b.dataset.d); if(j<0||j>=o.length) return;
    [o[i],o[j]]=[o[j],o[i]]; LS.set('dd-trans-order',o); drawToggles(b.dataset.mv+b.dataset.d); drawCmp(); });
  if(focus){ const b=ROOT.querySelector(`[data-mv="${focus.replace(/-?1$/,'')}"][data-d="${focus.endsWith('-1')?-1:1}"]`); (b&&!b.disabled?b:ROOT.querySelector(`[data-mv="${focus.replace(/-?1$/,'')}"]:not([disabled])`))?.focus(); }
}
function shown(r){
  if($('#fEdited').checked && r.t===r.t0) return false;
  if($('#fNote').checked && !r.note) return false;
  if($('#fCm').checked && !cmLeft(r)) return false;
  const q=$('#q').value.trim().toLowerCase(); if(q && ![r.o,r.r,r.t,r.note,...(r.cm||[]).map(c=>c.a+' '+c.b+' '+c.why)].some(x=>String(x||'').toLowerCase().includes(q))) return false;
  return true;
}
function rowHtml(r,cs){
  const L={o:DOC.cols.o,r:DOC.cols.r,t:DOC.cols.t};
  const cell=c=>c==='t'
    ? `<div class="c t${r.t?'':' empty'}" data-l="${esc(L.t)}" tabindex="0" role="button" aria-label="${esc(L.t)} 고치기">${r.t?esc(r.t):(r.o?'(번역 없음 — 눌러서 넣을 수 있음)':'')}</div>`
    : `<div class="c ${c}${c==='r'&&!r.r&&r.rc?' rc':''}" data-l="${esc(L[c])}"${c==='o'?' lang="en"':''}>${c==='r'&&!r.r&&r.rc?'↑ 위 줄 글에 함께 옮김':esc(r[c]||'')}</div>`;
  const tags=[r.t!==r.t0?'<span class="tag">✎ 고침</span>':'', !r.t0&&r.o?'<span class="tag only">원서에만 있는 글</span>':'', !r.o&&r.t0?'<span class="tag only">원서에 없는 글</span>':''].join('');
  return `<div class="tr${r.h?' h':''}${r.t!==r.t0?' edited':''}" id="tx-${esc(r.id)}" data-id="${esc(r.id)}">${cs.map(cell).join('')}
    <div class="meta">${r.op?`<span>${esc(r.op)}</span>`:''}${tags}${r.at?`<span>${esc(day(r.at))} 고침</span>`:''}
      ${(r.hist&&r.hist.length)||r.t!==r.t0?`<button type="button" data-act="hist">고친 기록${r.hist&&r.hist.length?` (${r.hist.length})`:''}</button>`:''}
      <button type="button" data-act="note">${r.note?'메모 고치기':'메모'}</button>
      <a href="${esc(hashFor(DOC.id,r.id))}" class="sm" aria-label="이 줄 주소">#</a></div>
    ${r.note?`<div class="note-show">📝 ${esc(r.note)}</div>`:''}${cmHtml(r)}</div>`;
}
function drawCmp(){
  const cs=cols(); const tmpl=cs.map(c=>c==='t'?'1.15fr':'1fr').join(' ');
  ROOT.style.setProperty('--cols',tmpl);
  $('#hdr').innerHTML=cs.map(c=>`<div>${esc(DOC.cols[c])}</div>`).join('');
  const list=DOC.rows.filter(shown);
  $('#cnt').textContent=`${list.length} / ${DOC.rows.length}줄 · 고친 줄 ${DOC.rows.filter(r=>r.t!==r.t0).length}${cmCnt()}`;
  $('#rows').innerHTML=list.map(r=>rowHtml(r,cs)).join('')||'<p class="sm" style="padding:10px">맞는 줄이 없습니다.</p>';
}
function redrawRow(r){ const el=rowEl(r.id); if(el){ el.outerHTML=rowHtml(r,cols()); } $('#cnt').textContent=`${DOC.rows.filter(shown).length} / ${DOC.rows.length}줄 · 고친 줄 ${DOC.rows.filter(x=>x.t!==x.t0).length}${cmCnt()}`; }

// 번역본만: 우리 번역 문단대로 이어서
function drawRead(){
  const out=[]; let cur=null;
  const flush=()=>{ if(cur&&cur.parts.length) out.push(`<p${cur.h?' class="h"':''}>${cur.parts.join(' ')}</p>`); cur=null; };
  for(const r of DOC.rows){
    if(!r.t) continue;
    const pieces=r.t.split('\n');
    pieces.forEach((pc,k)=>{
      if(!cur || (k===0&&r.np) || k>0 || r.h || cur.h) { flush(); cur={parts:[],h:!!r.h}; }
      if(pc.trim()) cur.parts.push(`<span class="s${r.t!==r.t0?' ed':''}" data-id="${esc(r.id)}" tabindex="0" role="link" title="눌러서 대조 보기로">${esc(pc)}</span>`);
    });
  }
  flush();
  $('#reader').innerHTML=out.join('');
  $('#reader').classList.toggle('marks',$('#fMarks').checked);
}
function setView(v,first){
  if(EDITING) finishEdit(true);
  VIEW=v; LS.set('dd-trans-view',v);
  $('#vCmp').setAttribute('aria-pressed',v==='cmp'); $('#vRead').setAttribute('aria-pressed',v==='read');
  $('#cmp').hidden=v!=='cmp'; $('#read').hidden=v!=='read';
  ROOT.querySelectorAll('#colToggles,#fEdited,#fNote,#q,#cnt,#fCm,#fCmOpen').forEach(x=>{ (x.closest('label')||x).style.display=v==='cmp'?'':'none'; });
  $('.rdOnly').style.display=v==='read'?'':'none';
  if(v==='cmp') drawCmp(); else drawRead();
}
$('#vCmp').onclick=()=>setView('cmp'); $('#vRead').onclick=()=>setView('read');
['#fEdited','#fNote','#fCm'].forEach(s=>$(s).onchange=drawCmp);
$('#fCmOpen').onchange=()=>{ LS.set('dd-trans-cmopen',$('#fCmOpen').checked); drawCmp(); };
$('#fMarks').onchange=()=>$('#reader').classList.toggle('marks',$('#fMarks').checked);
let qT; $('#q').oninput=()=>{ clearTimeout(qT); qT=setTimeout(drawCmp,250); };
const fz=d=>{ const v=Math.max(.8,Math.min(1.6,Math.round((LS.get('dd-trans-fz',1)+d)*10)/10)); LS.set('dd-trans-fz',v); ROOT.style.setProperty('--fz',v); };
$('#fzDn').onclick=()=>fz(-.1); $('#fzUp').onclick=()=>fz(.1);
$('#reader').addEventListener('click',e=>{ const s=e.target.closest('span.s'); if(s) openFromReader(s.dataset.id); });
$('#reader').addEventListener('keydown',e=>{ const s=e.target.closest('span.s'); if(s&&(e.key==='Enter'||e.key===' ')){ e.preventDefault(); openFromReader(s.dataset.id); } });
function openFromReader(id){ ['#fEdited','#fNote','#fCm'].forEach(s=>$(s).checked=false); $('#q').value=''; setView('cmp'); goRow(id,true); }
function goRow(id,edit){
  let el=rowEl(id);
  if(!el && BY[id]){ ['#fEdited','#fNote','#fCm'].forEach(s=>$(s).checked=false); $('#q').value=''; if(VIEW!=='cmp') setView('cmp'); else drawCmp(); el=rowEl(id); }
  if(!el) return;
  ROOT.querySelectorAll('.tr.cur').forEach(x=>x.classList.remove('cur')); el.classList.add('cur');
  el.scrollIntoView({block:'center'});
  if(edit) startEdit(BY[id]); else el.querySelector('.c.t').focus({preventScroll:true});
}

// ---------- 고치기 ----------
$('#rows').addEventListener('click',e=>{
  const tr=e.target.closest('.tr'); if(!tr) return; const r=BY[tr.dataset.id];
  const cmb=e.target.closest('[data-cm]'); if(cmb){ e.preventDefault(); cmAct(r,cmb); return; }
  if(e.target.closest('details.cm')) return;
  const act=e.target.closest('[data-act]');
  if(act){ e.preventDefault(); if(act.dataset.act==='hist') toggleHist(r,tr); if(act.dataset.act==='note') editNote(r,tr); return; }
  if(e.target.closest('.c.t') && !(EDITING&&EDITING.r===r)) startEdit(r);
});
$('#rows').addEventListener('keydown',e=>{
  const c=e.target.closest('.c.t'); if(c&&(e.key==='Enter'||e.key===' ')&&e.target===c){ e.preventDefault(); startEdit(BY[c.closest('.tr').dataset.id]); }
});
function startEdit(r){
  if(EDITING) finishEdit(true);
  const tr=rowEl(r.id); if(!tr) return; const c=tr.querySelector('.c.t');
  c.outerHTML=`<div class="c t-ed" data-l="${esc(DOC.cols.t)}"><label class="sr" for="ed-${esc(r.id)}">${esc(DOC.cols.t)} 고치기</label><textarea id="ed-${esc(r.id)}">${esc(r.t)}</textarea>
    <div class="ed-acts"><button type="button" class="b pri" data-e="save">저장 (Ctrl+Enter)</button><button type="button" class="b" data-e="next">저장하고 다음 줄</button><button type="button" class="b" data-e="cancel">취소 (Esc)</button>${r.t!==r.t0?'<button type="button" class="b" data-e="orig">처음 번역 넣기</button>':''}</div></div>`;
  const ta=tr.querySelector('textarea'); EDITING={r,ta};
  const fit=()=>{ ta.style.height='auto'; ta.style.height=Math.max(60,ta.scrollHeight+4)+'px'; }; fit(); ta.oninput=fit;
  ta.focus(); ta.setSelectionRange(ta.value.length,ta.value.length);
  ta.onkeydown=e=>{ if(e.key==='Escape'){ e.preventDefault(); finishEdit(false); }
    if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){ e.preventDefault(); finishEdit(true,e.shiftKey?null:'next'); } };
  tr.querySelector('.ed-acts').onclick=e=>{ const b=e.target.closest('[data-e]'); if(!b) return;
    if(b.dataset.e==='save') finishEdit(true); if(b.dataset.e==='next') finishEdit(true,'next'); if(b.dataset.e==='cancel') finishEdit(false);
    if(b.dataset.e==='orig'){ ta.value=r.t0; fit(); ta.focus(); } };
  ta.addEventListener('blur',()=>setTimeout(()=>{ if(EDITING&&EDITING.ta===ta&&!tr.contains(document.activeElement)) finishEdit(true); },150));
}
function finishEdit(save,then){
  if(!EDITING) return; const {r,ta}=EDITING; EDITING=null;
  const v=ta.value.replace(/\r\n/g,'\n');
  if(save && v!==r.t) saveRow(r,{t:v});
  redrawRow(r);
  if(then==='next'){ const list=DOC.rows.filter(shown); const i=list.indexOf(r); const nx=list.slice(i+1).find(x=>x.t||x.o); if(nx){ goRow(nx.id,true); } }
  else { const c=(rowEl(r.id)||ROOT).querySelector('.c.t'); if(c) c.focus({preventScroll:true}); }
}
function saveRow(r,patch){
  const before={t:r.t,note:r.note,hist:r.hist,at:r.at,cmDone:r.cmDone};
  if(patch.t!==undefined){ r.hist=[{t:r.t,at:r.at||''},...(r.hist||[])].slice(0,30); r.t=patch.t; r.at=new Date().toISOString(); }
  if(patch.note!==undefined) r.note=patch.note;
  if(patch.cmDone!==undefined) r.cmDone=patch.cmDone;
  PENDING++; say('저장하는 중…');
  QUEUE=QUEUE.then(async()=>{
    try{ const res=await api('?id='+encodeURIComponent(DOC.id),{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({row:r.id,...patch})});
      const j=await res.json().catch(()=>({})); if(!res.ok) throw new Error(j.error||res.status);
      Object.assign(r,j.row); PENDING--; say(PENDING?'저장하는 중…':'저장했습니다 ('+day(j.updated)+')'); if(!(EDITING&&EDITING.r===r)) redrawRow(r);
    }catch(e){ PENDING--; Object.assign(r,before); redrawRow(r); say('저장하지 못했습니다: '+e.message+' — 인터넷 연결을 확인하고 다시 고쳐 주세요.',true); }
  });
}
// ---------- 교정 의견 (운영자 요청, 2026-11-28) ----------
// 교정안은 '메따·계발·위빠사나'로 바뀐 원고를 보고 만든 것 — 이 자료의 표기(멧따·개발·위빳사나)로 맞춰 찾고 넣는다(글자 수가 같음).
const CM_VOC=[['메따','멧따'],['계발','개발'],['위빠사나','위빳사나']];
function cmN(x){ for(const [a,b] of CM_VOC) x=x.split(a).join(b); return x; }
function cmFind(t,a){ const idx=[]; let ns=''; for(let i=0;i<t.length;i++){ if(!/\s/.test(t[i])){ idx.push(i); ns+=t[i]; } }
  const na=cmN(String(a||'').replace(/\s+/g,'')); if(!na) return null; const j=cmN(ns).indexOf(na); return j<0?null:[idx[j],idx[j+na.length-1]+1]; }
function cmLeft(r){ if(!r.cm) return 0; const d=new Set(r.cmDone||[]); return r.cm.filter(c=>!d.has(c.n)).length; }
function cmCnt(){ const all=DOC.rows.reduce((n,r)=>n+(r.cm?r.cm.length:0),0); if(!all) return ''; const left=DOC.rows.reduce((n,r)=>n+cmLeft(r),0); return ` · 교정 의견 ${all}개 중 남은 것 ${left}`; }
function cmHtml(r){
  if(!r.cm||!r.cm.length) return '';
  const done=new Set(r.cmDone||[]); const left=r.cm.filter(c=>!done.has(c.n)).length;
  return `<details class="box cm"${LS.get('dd-trans-cmopen',true)?' open':''}><summary>💬 교정 의견 ${r.cm.length}개${left<r.cm.length?` · 넣음 ${r.cm.length-left}`:''}</summary><ol>${r.cm.map(c=>cmItem(r,c,done.has(c.n))).join('')}</ol></details>`;
}
function cmItem(r,c,isDone){
  const f=c.to?null:cmFind(r.t,c.a), nb=cmN(c.b), need=/\[역자 번역 필요/.test(c.b);
  const mk=`<button type="button" class="b" data-cm="mark" data-n="${c.n}">반영함으로 표시</button>`;
  let act;
  if(isDone) act=`<span class="cm-ok">✓ 반영함</span> <button type="button" class="b" data-cm="unmark" data-n="${c.n}">표시 풀기</button>`;
  else if(c.to) act=`<span class="sm">다음 줄까지 이어지는 글이라 직접 고쳐 주세요.</span> `+mk;
  else if(need) act=`<span class="sm">원문 한 문단이 빠진 곳 — 직접 번역해 넣어 주세요.</span> `+mk;
  else if(f && r.t.slice(f[0],f[1])===nb) act=`<span class="sm">이 자료에는 이미 수정안대로 되어 있습니다.</span> `+mk;
  else if(f) act=`<button type="button" class="b pri" data-cm="apply" data-n="${c.n}">수정안 넣기</button> `+mk;
  else act=`<span class="sm">지금 우리 번역에서 ‘현재 표현’을 찾지 못했습니다 (이미 고쳤거나 원고 글이 다름).</span> `+mk;
  return `<li class="${isDone?'done':''}"><div class="cm-h"><span class="cm-tag">${esc(c.tag)}</span>${c.star?'<span class="cm-star" title="2차 대조에서 새로 찾은 항목">★</span>':''} <span class="sm">${c.g===1?'1부 뜻':'2부 문체·표기'} · ${esc(c.sec)} · 원고 ${c.p}문단 · #${c.n}</span></div><div class="cm-ab"><span class="cm-l">현재</span> <span class="cm-a">${esc(c.a)}</span></div><div class="cm-ab"><span class="cm-l">수정안</span> <span class="cm-b">${esc(c.b)}</span></div>${c.why?`<div class="cm-why">${esc(c.why)}</div>`:''}${c.en?`<div class="cm-en" lang="en">원문: ${esc(c.en)}</div>`:''}${c.k!=='exact'?'<div class="sm">교정안이 본 원고와 글이 조금 달라, 가장 비슷한 줄에 붙였습니다.</div>':''}<div class="cm-act">${act}</div></li>`;
}
function cmAct(r,b){
  const n=+b.dataset.n, c=(r.cm||[]).find(x=>x.n===n); if(!c) return; const done=(r.cmDone||[]).filter(x=>x!==n);
  if(b.dataset.cm==='unmark'){ saveRow(r,{cmDone:done}); redrawRow(r); return; }
  if(b.dataset.cm==='mark'){ saveRow(r,{cmDone:[...done,n]}); redrawRow(r); return; }
  if(b.dataset.cm==='apply'){ const f=cmFind(r.t,c.a); if(!f){ say('‘현재 표현’을 찾지 못했습니다.',true); return; }
    saveRow(r,{t:r.t.slice(0,f[0])+cmN(c.b)+r.t.slice(f[1]),cmDone:[...done,n]}); redrawRow(r);
    const el=rowEl(r.id); if(el){ const d=el.querySelector('details.cm'); if(d) d.open=true; const nx=el.querySelector('[data-cm="apply"],[data-cm="mark"]'); (nx||el.querySelector('.c.t')).focus({preventScroll:true}); } }
}
function cmPolicy(){
  const I=DOC.cmInfo, box=$('#cmPol'); ROOT.querySelectorAll('.cmopt').forEach(x=>x.hidden=!DOC.rows.some(r=>r.cm));
  $('#fCmOpen').checked=LS.get('dd-trans-cmopen',true);
  if(!I){ box.hidden=true; return; } box.hidden=false;
  box.innerHTML=`<summary>💬 교정 의견 안내 · 책 전체 방침으로 정할 것 (${(I.policy||[]).length})</summary>
    <p class="sm">${esc(I.title)}${I.at?' · 넣은 날 '+esc(day(I.at)):''}</p>${(I.intro||[]).filter(x=>!/Ctrl\+F/.test(x)).map(x=>`<p>${esc(x)}</p>`).join('')}
    <p class="sm">교정안은 ‘메따·계발·위빠사나’로 바뀐 원고를 보고 만든 것이라, ‘수정안 넣기’는 이 자료의 표기(멧따·개발·위빳사나)로 바꿔 넣습니다.</p>
    <dl>${(I.policy||[]).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>`;
}
function toggleHist(r,tr){
  const old=tr.querySelector('.box.hist'); if(old){ old.remove(); return; }
  const h=r.hist||[];
  const b=document.createElement('div'); b.className='box hist';
  b.innerHTML=`<b>고친 기록</b> <span class="sm">(가장 최근 것이 위)</span><ol>${h.map((x,i)=>`<li>${esc(x.t)||'<i>(빈 글)</i>'}<div class="sm">${x.at?esc(day(x.at))+'까지의 글':'처음 번역'} · <button type="button" class="b" data-back="${i}">이 글로 되돌리기</button></div></li>`).join('')}</ol>
    <div class="sm" style="margin-top:6px">처음 번역: ${esc(r.t0)||'(없음)'} ${r.t!==r.t0?`<button type="button" class="b" data-back="orig">처음 번역으로 되돌리기</button>`:''}</div>`;
  b.onclick=e=>{ const x=e.target.closest('[data-back]'); if(!x) return; const v=x.dataset.back==='orig'?r.t0:h[+x.dataset.back].t; if(v!==r.t) saveRow(r,{t:v}); redrawRow(r); };
  tr.appendChild(b);
}
function editNote(r,tr){
  const old=tr.querySelector('.box.nt'); if(old){ old.remove(); return; }
  const b=document.createElement('div'); b.className='box nt';
  b.innerHTML=`<label for="nt-${esc(r.id)}"><b>메모</b> <span class="sm">(교정하면서 남길 말 — 번역본에는 들어가지 않습니다)</span></label><textarea id="nt-${esc(r.id)}" style="width:100%;min-height:50px;font:inherit;border:1px solid var(--line);border-radius:8px;padding:6px 8px;background:var(--paper);color:var(--ink)">${esc(r.note||'')}</textarea>
    <div class="ed-acts"><button type="button" class="b pri" data-n="save">메모 저장</button><button type="button" class="b" data-n="cancel">닫기</button>${r.note?'<button type="button" class="b" data-n="del">메모 지우기</button>':''}</div>`;
  b.onclick=e=>{ const x=e.target.closest('[data-n]'); if(!x) return; const ta=b.querySelector('textarea');
    if(x.dataset.n==='save'){ if(ta.value!==(r.note||'')) saveRow(r,{note:ta.value}); redrawRow(r); }
    if(x.dataset.n==='del'){ saveRow(r,{note:''}); redrawRow(r); }
    if(x.dataset.n==='cancel') b.remove(); };
  tr.appendChild(b); b.querySelector('textarea').focus();
}
addEventListener('beforeunload',e=>{ if(PENDING||EDITING&&EDITING.ta.value!==EDITING.r.t){ e.preventDefault(); e.returnValue=''; } });

// ---------- 내려받기 ----------
function download(name,text,type){ const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([text],{type})); a.download=name; document.body.appendChild(a); a.click(); setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500); }
const stamp=()=>{ const d=new Date(); return `${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}`; };
$('#dlTxt').onclick=()=>{
  const ps=[]; let cur=null;
  for(const r of DOC.rows){ if(!r.t) continue; r.t.split('\n').forEach((pc,k)=>{ if(!cur||(k===0&&r.np)||k>0||r.h||cur.h){ if(cur) ps.push(cur.s.join(' ')); cur={s:[],h:!!r.h}; } if(pc.trim()) cur.s.push(pc.trim()); }); }
  if(cur) ps.push(cur.s.join(' '));
  download(`${DOC.title.replace(/[\\/:*?"<>|]/g,'')}_번역본_${stamp()}.txt`,'﻿'+ps.filter(Boolean).join('\r\n\r\n')+'\r\n','text/plain;charset=utf-8');
};
$('#dlCsv').onclick=()=>{
  const q=s=>'"'+String(s??'').replace(/"/g,'""')+'"';
  const hasR=DOC.rows.some(r=>r.r);
  const od=order(), H={o:[DOC.cols.o],r:[DOC.cols.r],t:['처음 번역','고친 번역']}, V={o:r=>[r.o],r:r=>[r.r],t:r=>[r.t0,r.t]};
  const hasCm=DOC.rows.some(r=>r.cm); const head=['번호','원서 쪽',...od.flatMap(c=>H[c]),'고침','메모',...(hasCm?['교정 의견']:[])];
  const lines=[head.map(q).join(',')].concat(DOC.rows.map((r,i)=>[i+1,r.op,...od.flatMap(c=>V[c](r)),r.t!==r.t0?'고침':'',r.note||'',...(hasCm?[(r.cm||[]).map(c=>`#${c.n} [${c.tag}] ${c.a} → ${c.b}${(r.cmDone||[]).includes(c.n)?' (넣음)':''}`).join('\n')]:[])].map(q).join(',')));
  download(`${DOC.title.replace(/[\\/:*?"<>|]/g,'')}_대조표_${stamp()}.csv`,'﻿'+lines.join('\r\n'),'text/csv;charset=utf-8');
};
start();

}
window.ddTrans={mount};
})();
