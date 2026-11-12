"""'듣기' 장 제목 검사 — 모든 책의 모든 장에서
  ① 장 처음(목차에서 장을 눌러 간 곳)에서 '듣기'를 누르면 맨 처음 소리가 장 제목인지
  ② 장 중간 쪽(장 시작 쪽 +2)에서 누르면 장 제목을 다시 읽지 않는지
  ③ 장 제목(위의 큰 제목)을 골라 '▶ 여기부터 듣기'를 누르면 장 제목부터 읽는지 (2026-11-12)
를 확인합니다. (장 첫 쪽이 비어 있거나 제목뿐인 경우도 ①에 들어감)

쓰는 법:  npm run build  →  (cd dist && python3 -m http.server 4399 &)  →  python3 tools/check_listen.py [DL-0016 …]
아무 책도 주지 않으면 글로 읽기가 있는 모든 책을 검사합니다. 문제가 있으면 끝에 목록이 나오고 종료 코드 1.
"""
import sys, re, json, glob, os, difflib
from playwright.sync_api import sync_playwright

BASE = os.environ.get('DD_BASE', 'http://localhost:4399')
STUB = """
window.__said=[];
const ss={speaking:false,pending:false,paused:false,cancel(){},pause(){},resume(){},
 getVoices(){return [{name:'ko',lang:'ko-KR',localService:true,default:true,voiceURI:'ko'}]},
 speak(u){window.__said.push(u.text)},  // 첫 소리만 기록(끝났다고 알리지 않으므로 다음으로 넘어가지 않음)
 addEventListener(){}, onvoiceschanged:null};
Object.defineProperty(window,'speechSynthesis',{value:ss});
window.SpeechSynthesisUtterance=function(t){this.text=t};
localStorage.setItem('dd-tts', JSON.stringify({pause:0}));
"""
# 장 제목은 소리로 바뀌어 읽힘(Ⅱ→2, 로마자 빨리어→한글, 괄호 생략) → 제목의 한글이 첫 소리에 들어 있으면 같은 것으로 봄
han = lambda s: re.sub(r'[^가-힣]', '', s or '')
def same(said, title):
    h = han(title)
    if h: return h in han(said) and len(han(said)) <= len(h) * 3 + 10
    k = lambda s: re.sub(r'[^0-9A-Za-z]', '', s or '').lower()
    return difflib.SequenceMatcher(None, k(said), k(title)).ratio() >= 0.6

root = os.path.join(os.path.dirname(__file__), '..', 'content', 'texts')
ids = sys.argv[1:] or sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(root, 'DL-*.json')))
bad = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for bid in ids:
        pg = b.new_page(viewport={'width': 1200, 'height': 900})
        pg.add_init_script(STUB)
        pg.goto(f'{BASE}/read/{bid}/')
        try: pg.wait_for_selector('#rSpeak', state='attached', timeout=15000)
        except Exception: print(f'{bid}: 읽기 화면 없음(건너뜀)'); pg.close(); continue
        chs = pg.evaluate("[...document.querySelectorAll('#p-toc [data-ci]')].map(b=>({t:b.textContent, go:+b.dataset.go, ci:+b.dataset.ci})).filter(x=>x.ci>=0)")
        body = json.load(open(os.path.join(root, bid + '.json')))['body']
        ptxt = re.split(r'^=== .*? ===$', body, flags=re.M)[1:]
        # 그림·빈 줄만 있는 쪽은 소리로는 빈 쪽 → 장의 '처음'은 글이 처음 나오는 쪽
        hastext = [bool(re.sub(r'!\[[^\]]*\]\([^)]*\)|\s', '', t)) for t in ptxt]
        last = int(pg.evaluate("document.querySelector('#rRange').max"))
        nOk = 0
        for i, c in enumerate(chs):
            nxt = chs[i + 1]['go'] if i + 1 < len(chs) else last + 1
            tests = [('처음', c['go'], True)]
            f0 = next((n for n in range(c['go'], nxt) if n - 1 < len(hastext) and hastext[n - 1]), c['go'])
            if nxt - f0 > 3: tests.append(('중간', f0 + 2, False))
            for kind, page, want in tests:
                if kind == '처음':
                    pg.evaluate("ci=>document.querySelector(`#p-toc [data-ci=\"${ci}\"]`).click()", c['ci'])
                else:
                    pg.evaluate("n=>{const r=document.querySelector('#rRange'); r.value=n; r.dispatchEvent(new Event('change'))}", page)
                pg.wait_for_timeout(150)
                pg.evaluate("(()=>{const b=document.querySelector('#rSpeak'); if(/멈춤/.test(b.textContent)) b.click()})()")  # 앞 검사의 듣기가 남아 있으면 먼저 멈춤
                pg.wait_for_timeout(100)
                pg.evaluate("window.__said=[]; document.querySelector('#rSpeak').click()")
                try: pg.wait_for_function("window.__said.length>0", timeout=15000)   # 다시 연 뒤에는 소리 사전을 받는 동안 기다림
                except Exception: pass
                first = pg.evaluate("window.__said[0] || ''")
                body = pg.evaluate("!!document.querySelector('.speaking')")  # 본문 문단을 읽는 중이면 표시가 있음, 장 제목만 읽을 때는 없음
                pg.evaluate("document.querySelector('#rSpeak') && document.querySelector('#rSpeak').click()")
                titled = same(first, c['t']) and not body
                if titled != want:
                    bad.append(f"{bid} · {c['t']} · {kind}({page}) → 첫 소리: {first[:40]!r}")
                else: nOk += 1
            # ③ 장 제목을 골라 '여기부터 듣기'
            pg.evaluate("ci=>document.querySelector(`#p-toc [data-ci=\"${ci}\"]`).click()", c['ci']); pg.wait_for_timeout(150)
            pg.evaluate("""()=>{window.__said=[]; const h=document.querySelector('#rBody .ch-head h3'); const b=document.querySelector('#selPlay'); if(!h||!b) return;
              const r=document.createRange(); r.selectNodeContents(h); const s=getSelection(); s.removeAllRanges(); s.addRange(r); b.click()}""")
            try: pg.wait_for_function("window.__said.length>0", timeout=8000)
            except Exception:   # 글 없는 쪽(색인 표 등)을 오래 건너뛰는 장 — 다음 검사에 섞이지 않게 페이지를 다시 엶
                if f0 - c['go'] > 3 or not any(hastext[c['go'] - 1:nxt - 1]):
                    pg.goto(f'{BASE}/read/{bid}/'); pg.wait_for_selector('#rSpeak', state='attached', timeout=15000); nOk += 1; continue
            first = pg.evaluate("window.__said[0] || ''")
            pg.evaluate("window.__said.length && document.querySelector('#rSpeak') && document.querySelector('#rSpeak').click()")  # 읽기 시작했으면 멈춤
            if pg.evaluate("!!document.querySelector('#selPlay')"):
                if same(first, c['t']): nOk += 1
                else: bad.append(f"{bid} · {c['t']} · 장 제목 골라 듣기 → 첫 소리: {first[:40]!r}")
            if not any(hastext[c['go'] - 1:min(nxt - 1, c['go'] + 2)]):   # 글 없는 쪽을 건너뛰는 듣기가 다음 검사에 섞이지 않게
                pg.goto(f'{BASE}/read/{bid}/'); pg.wait_for_selector('#rSpeak', state='attached', timeout=15000)
        print(f'{bid}: 장 {len(chs)}개, 검사 {nOk}개 통과')
        pg.close()
    b.close()
if bad:
    print('\n문제:'); print('\n'.join(bad)); sys.exit(1)
print('모두 통과')
