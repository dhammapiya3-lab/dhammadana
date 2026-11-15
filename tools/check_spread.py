"""양쪽으로 보기 줄 맞춤 검사 — 텍스트 JSON 에 `ly`(인쇄본 줄 높이)가 있는 책에서,
인쇄본에서 같은 높이(±4pt)에 있는 왼쪽 줄과 오른쪽 줄(둘 중 하나는 문단 첫 줄 — 문단 안의 줄 사이는 화면에서 바꿀 수 없으므로)이 화면에서도 같은 높이인지 모든 장을 넘기며 봅니다.

쓰는 법:  npm run build  →  (cd dist && python3 -m http.server 4399 &)  →  python3 tools/check_spread.py [DL-0026 …]
"""
import sys, os, json
from playwright.sync_api import sync_playwright

BASE = os.environ.get('DD_BASE', 'http://localhost:4399')
ids = sys.argv[1:] or ['DL-0026']
PROBE = """async (id) => {
  window.__ly = window.__ly || (await (await fetch('/texts/' + id + '.json')).json()).ly;
  const ly = window.__ly, out = [];
  const tops = p => { const t = []; let k = 0, want = true; const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    for (let n = w.nextNode(); n; n = w.nextNode()) { if (n.nodeType === 1) { if (n.tagName === 'BR') { k++; want = true; } continue; }
      if (!want || !n.nodeValue.trim()) continue; const r = document.createRange(), i = n.nodeValue.search(/\\S/); r.setStart(n, i); r.setEnd(n, i + 1);
      const b = r.getClientRects()[0]; if (b) t[k] = b.top; want = false; } return t; };
  const lines = col => { const L = []; col.querySelectorAll('p[data-s]').forEach(p => { if (!p.offsetParent) return; const ys = (ly[p.dataset.pg] || [])[+p.dataset.s] || [], ts = tops(p);
    ys.forEach((y, k) => { if (y != null && ts[k] != null) L.push({ y, t: ts[k], first: k === ys.findIndex(v => v != null), s: p.textContent.slice(0, 30), pg: p.dataset.pg }); }); }); return L; };
  document.querySelectorAll('.spr-pg.spr-l').forEach(Lc => { const Rc = Lc.nextElementSibling; if (!Rc || !Rc.classList.contains('spr-r')) return;
    const A = lines(Lc), B = lines(Rc);
    A.forEach(a => { const b = B.filter(b => Math.abs(b.y - a.y) <= 4 && (a.first || b.first)).sort((p, q) => Math.abs(p.y - a.y) - Math.abs(q.y - a.y))[0];
      if (b && Math.abs(b.t - a.t) > 8) out.push({ pg: a.pg, py: a.y, d: Math.round(b.t - a.t), l: a.s, r: b.s }); }); });
  return out;
}"""
tot = 0
with sync_playwright() as p:
    br = p.chromium.launch()
    for bid in ids:
        pg = br.new_page(viewport={'width': 1500, 'height': 950})
        pg.add_init_script(f"localStorage.setItem('dd-rspread2-{bid}','1')")
        pg.goto(f'{BASE}/read/{bid}/'); pg.wait_for_selector('#p-toc [data-ci]', state='attached', timeout=20000)
        chs = pg.evaluate("[...document.querySelectorAll('#p-toc [data-ci]')].map(b=>+b.dataset.ci).filter(x=>x>=0)")
        bad = []
        for ci in sorted(set(chs)):
            pg.evaluate("ci=>document.querySelector(`#p-toc [data-ci=\"${ci}\"]`).click()", ci)
            pg.wait_for_timeout(900)
            bad += pg.evaluate(PROBE, bid)
        seen = set(); uniq = []
        for b in bad:
            k = (b['pg'], b['py'])
            if k not in seen: seen.add(k); uniq.append(b)
        for b in uniq: print(f"  {bid} 쪽순번 {b['pg']} 인쇄 {b['py']}pt: 오른쪽이 {b['d']:+}px | {b['l']} ↔ {b['r']}")
        print(f'{bid}: 어긋난 줄 {len(uniq)}'); tot += len(uniq)
    br.close()
print('모두 맞음' if not tot else f'어긋난 줄 모두 {tot}')
