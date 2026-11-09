"""아래 바 › 검사 — 모든 책을 처음부터 끝까지 › 로 넘기며, 멈춘 곳 맨 위가 소제목(또는 장 제목)인지 확인합니다.
사진·쪽 표시·하늘색 강조·보통 문단에 멈추면 문제로 적습니다.

쓰는 법:  npm run build  →  (cd dist && python3 -m http.server 4399 &)  →  python3 tools/check_nav.py [DL-0011 …]
"""
import sys, os, glob, json
from playwright.sync_api import sync_playwright

BASE = os.environ.get('DD_BASE', 'http://localhost:4399')
root = os.path.join(os.path.dirname(__file__), '..', 'content', 'texts')
ids = sys.argv[1:] or sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(root, 'DL-*.json')))
PROBE = """() => {
  const b = document.querySelector('#rBody'), rt = document.querySelector('.r-top'), on = !document.querySelector('#reader').classList.contains('chrome-off');
  const top = Math.max(b.getBoundingClientRect().top, on && rt ? rt.getBoundingClientRect().bottom : 0);  // 위 메뉴가 떠 있으면 그 아래부터가 보이는 곳
  const ch = (document.querySelector('.r-title small') || {}).textContent || '';
  if (b.scrollTop < 4) return { kind: 'chapter', ch, text: '' };  // 장 처음
  if (b.scrollTop >= b.scrollHeight - b.clientHeight - 2) return { kind: 'end', ch, text: '' };  // 장 끝까지 내려감(마지막 소제목이 화면 아래쪽)
  const els = [...b.querySelectorAll('p, img, .pmark, .r-toc, figure, h4, table')].filter(e => { const r = e.getBoundingClientRect(); return r.height > 0 && r.bottom > top + 4; });
  const e = els[0]; if (!e) return { kind: 'none', ch, text: '' };
  const t = e.textContent.trim(), s = e.firstElementChild;
  const bold = e.tagName === 'P' && e.children.length === 1 && s && s.tagName === 'STRONG' && s.textContent.trim() === t;
  const kind = e.classList.contains('sub-h') ? 'sub-h' : bold ? 'bold' : e.tagName === 'IMG' || e.closest('figure') ? 'image' : e.classList.contains('pmark') ? 'page-mark' : e.querySelector('.hl') ? 'colored' : 'para';
  return { kind, ch, text: t.slice(0, 50), pg: e.dataset.pg || (e.closest('[data-pg]') || {dataset:{}}).dataset.pg };
}"""
bad = []
with sync_playwright() as p:
    br = p.chromium.launch()
    for bid in ids:
        pg = br.new_page(viewport=({'width': 390, 'height': 800} if os.environ.get('NAV_MOBILE') else {'width': 1280, 'height': 800}))
        pg.add_init_script(f"localStorage.setItem('dd-pos-{bid}','1')")
        pg.goto(f'{BASE}/read/{bid}/')
        try: pg.wait_for_selector('#rNext', state='attached', timeout=15000)
        except Exception: print(bid, '읽기 화면 없음'); pg.close(); continue
        pg.evaluate("()=>{const c=document.querySelector('#p-toc [data-ci]'); c && c.click()}"); pg.wait_for_timeout(150)
        stops, prev, same = 0, None, 0
        for i in range(3000):
            if pg.evaluate("document.querySelector('#rNext').disabled"): break
            # 사람이 메뉴를 띄워 놓고 › 를 누르는 것처럼 (메뉴가 글을 가리는지도 검사)
            pg.evaluate("document.querySelector('#reader').classList.remove('chrome-off'); document.querySelector('#rNext').click()"); pg.wait_for_timeout(60)
            r = pg.evaluate(PROBE); stops += 1
            key = (r['ch'], r['text'], r['kind'])
            if key == prev:
                same += 1
                if same > 3:
                    if pg.evaluate("(()=>{const r=document.querySelector('#rRange');return +r.value>=+r.max-3})()"): break  # 책 끝
                    bad.append(f"{bid} · {r['ch']} · 같은 곳에서 더 나가지 않음"); break
                continue
            same = 0; prev = key
            if os.environ.get('NAV_ALL'): print('  ', r)
            if r['kind'] not in ('chapter', 'sub-h', 'bold', 'end'):
                bad.append(f"{bid} · {r['ch'].split('·')[-1].strip()} · {r.get('pg')} · {r['kind']}: {r['text']}")
        print(f'{bid}: {stops}번 넘김')
        pg.close()
    br.close()
print('\n'.join(bad) if bad else '모두 소제목·장 제목에 멈춤')
sys.exit(1 if bad else 0)
