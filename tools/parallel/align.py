"""원서 대조 짝짓기 — 한국어 글로 읽기 본문(content/texts/<ID>.json)과 원서 문단 목록을 문장마다 짝지어
content/parallel/<ID>.<말>.json 을 만든다. (운영자 요청, 2026-11-15 — 다른 곳에도 쓸 수 있게 짝 자료를 따로 저장)

  python3 tools/parallel/align.py DL-0014 en tools/out/parallel/DL-0014.en.paras.json [--title …] [--by …] [--source …]

방법:
1. 한국어: 읽기 화면과 같은 단위(쪽 순번 n, 문단 순번 s)로 문단을 나눔. 각주([^n]:)·차례(%%)·그림 문단은 짝짓지 않음.
   원서: 원서 문단(쪽 이름 pg, 종류 k: h 제목·p 문단·sep 구분).
2. 문장 나누기: 마침표·물음표·느낌표(+닫는 따옴표) 뒤, 문단 안의 줄 바꿈.
3. LaBSE(여러 말을 함께 이해하는 문장 비교 모델)로 문장마다 뜻 벡터를 만들고,
   순서를 지키며(앞뒤가 엇갈리지 않게) 1:1·1:2·2:1·2:2·1:3·3:1 묶음과 건너뛰기를 허용하는 최적 짝짓기(동적 계획법).
4. 문장 짝으로 이어진 한국어 문단·원서 문단을 하나의 '문단 묶음'으로 모음(문단 나란히 보기에 씀).
5. 짝마다 점수(0~1, 뜻이 얼마나 같은지)를 남기고 낮은 짝은 확인 목록(report)으로.
글자는 한국어 본문도 원서도 한 자도 바꾸지 않음 — 짝 자료에는 각 문장이 문단의 몇 번째 글자부터 몇 번째까지인지만 적음.
"""
import sys, re, json, os, argparse, datetime
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('book'); ap.add_argument('lang'); ap.add_argument('orig')
ap.add_argument('--gl-start', default=None, help='용어 풀이가 시작하는 한국어 문단(정규식, 예: "^\\*\\*깜마\\[")');
ap.add_argument('--gl-end', default=None, help='용어 풀이가 끝난 뒤 첫 한국어 문단(정규식) — 그 뒤(역자 후기·판권지 등)는 짝짓지 않음')
ap.add_argument('--gl-nl', action='store_true', help="용어 풀이가 '낱말(roman)⏎풀이' 모양(DL-0011) — 쪽에서 잘린 낱말 조각('**웨**' + '**다나(vedanā)**')도 이어 읽음")
ap.add_argument('--pin', action='append', default=[], help='짝을 손으로 정함: "한국어 열쇠+…=원서 번호+…" (예 "1:0=0+1" 속표지 ↔ 원서 제목·지은이). 원서 쪽을 비우면("2:0+2:1=") 그 한국어 문단은 짝 없음');
ap.add_argument('--fnpin', action='append', default=[], help='각주 짝을 손으로: "한국어 각주 번호=원서 각주 번호" (예 "40=33"), 짝 없음은 "14=" 또는 "=3"');
ap.add_argument('--move', action='append', default=[], help='한국어판이 원서와 순서를 바꿔 옮긴 곳: "원서 A-B>C" — 원서 문단 A~B 를 C(번호 또는 @글 첫머리) 앞으로 옮겨 짝짓고, 그 묶음에 순서가 다르다는 메모(note)를 붙임 (DL-0001 Ⅳ장)')
ap.add_argument('--base', type=float, default=0.0, help='짝짓기 점수에서 뺄 바탕 뜻 비슷함 — 미얀마어처럼 관계없는 문장도 뜻 비슷함이 높게 나오는 말에서, 줄여 옮긴 곳을 억지로 짝짓지 않고 건너뛰게 (DL-0001: 0.25)')
ap.add_argument('--my-comma', action='store_true', help="미얀마어 원서의 말끝(…တယ်၊ …ဘူး၊ 등) 뒤 '၊' 에서도 문장을 나눔 — 법문을 받아 적은 책은 '။' 대신 '၊' 로 말을 이어 적어 한 문단이 한 문장이 됨 (DL-0001)")
ap.add_argument('--en-semi', action='store_true', help="원서 문장을 쌍반점(;) 뒤에서도 나눔 — 보디 스님 니까야 번역처럼 되풀이 구절을 ; 로 길게 이은 원서를 한국어판이 여러 문장으로 옮긴 곳 (DL-0022)")
ap.add_argument('--en-drop', action='append', default=[], help='한국어판에 없는 원서 문장(정규식, 문장 첫머리부터)은 짝짓기에서 빼고 원서만 있는 줄로 둠 — 예 MN10 의 선반공 비유 (DL-0022)')
ap.add_argument('--ko-join', action='store_true', help='쪽이 넘어가며 한국어 문장이 두 문단으로 갈라진 곳(앞 문단이 문장 끝 부호 없이 끝남)은 한 문장으로 짝지음 (DL-0022)')
ap.add_argument('--ko-dots', action='store_true', help="한국어의 줄임표 '...'·'…' 뒤에서는 문장이 끝난 말(…다·…요·…까 등) 뒤가 아니면 나누지 않음 — 되풀이를 줄임표로 줄인 번역 (DL-0022)")
ap.add_argument('--band', type=int, default=40, help='2단계 짝짓기 띠 너비(문장 수)')
ap.add_argument('--seg', action='append', default=[], help='짝짓기를 넘지 않을 경계: "한국어 열쇠=원서 번호 또는 @글 첫머리" — 여러 권을 묶은 책에서 권마다 따로 짝지음 (DL-0001)')
ap.add_argument('--ko-skip', action='append', default=[], help="원서에 없는 한국어 부분을 짝짓기에서 뺌: '시작 정규식|끝 정규식' (끝 문단은 남김, 끝을 비우면 책 끝까지) — 예 DL-0012 부록 2~역자 후기")
ap.add_argument('--ko-none', action='append', default=[], help="이 정규식에 맞는 한국어 문단은 짝짓지 않음 — 예 DL-0015 '^>> 《' (한국어판이 인용 끝에 단 경전 출처 줄)")
ap.add_argument('--kind-base', action='append', default=[], help="원서 문단 종류마다 짝짓기 점수에서 더 뺄 값: '종류=값' — 예 DL-0015 'note=0.15' (편자의 풀이 글은 한국어판이 일부만 옮겨 덜 끌어당기게)")
ap.add_argument('--toc', action='store_true', help='차례도 줄마다 짝지음 — 한국어 차례(%% 문단)의 제목 줄 ↔ 원서 차례(k toc) 항목, 쪽 번호는 빼고 제목끼리 (운영자 요청, 2026-11-17)')
ap.add_argument('--title', default=''); ap.add_argument('--by', default=''); ap.add_argument('--source', default='')
A = ap.parse_args()
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = json.load(open(os.path.join(REPO, 'content/texts', A.book + '.json')))
ORIG = json.load(open(A.orig))

# ---------- 한국어 문단 (app.js paras 와 같은 규칙) ----------
body = T['body'].replace('\r\n', '\n')
pages = []
for m in re.finditer(r'^===\s*(.*?)\s*===\s*$', body, flags=re.M):
    pages.append([m.group(1), m.end()])
for i, p in enumerate(pages):
    end = pages[i + 1][1] - len(re.search(r'===[^\n]*===\s*$', body[:pages[i + 1][1]]).group(0)) if i + 1 < len(pages) else len(body)
    p.append(body[p[1]:end].strip())


def paras(t): return [ '\n'.join(l.strip() for l in s.strip().split('\n')) for s in re.split(r'\n\s*\n', t or '') if s.strip()]


def plain(s):
    """화면에 보이는 글(표시 기호 뺌) — 문장 나누기·뜻 비교용"""
    s = re.sub(r'\[\^[^\]]+\]', '', s)
    s = re.sub(r'^(## |\^\^ |:: |>> |\+\+ |\|\| |%% )', '', s, flags=re.M)
    return re.sub(r'\*\*|==|°°|§§|@@|\{\{|\}\}', '', s)


KO = []   # {key:'n:s', t: 원문(본문 글 그대로), kind}
for n, (lab, _, txt) in enumerate(pages, 1):
    for s, para in enumerate(paras(txt)):
        if re.match(r'\[\^[^\]]+\]:', para) or para.startswith('%%') or para.startswith('![') or para.startswith('|'): continue
        KO.append({'key': f'{n}:{s}', 'pg': lab, 't': para, 'h': para.startswith('## ')})

# 빠알리 용어 풀이(가나다순으로 다시 늘어놓아 원서와 순서가 다름) — 차례 짝짓기에서 빼고 낱말(로마자)로 따로 짝지음
GL0 = next((i + 2 for i, p in enumerate(KO) if re.match(r'## IV\.', p['t'])), len(KO))
if A.gl_start: GL0 = next((i for i, p in enumerate(KO) if re.search(A.gl_start, p['t'])), len(KO))
GLE = len(KO)
if A.gl_end: GLE = next((i for i, p in enumerate(KO) if i > GL0 and re.search(A.gl_end, p['t'])), len(KO))
KO_GL = KO[GL0:GLE]; KO_DP = KO[:GL0]
for sk in A.ko_skip:   # 원서에 없는 부분(--ko-skip)
    s0, _, s1 = sk.partition('|')
    i0 = next((i for i, p in enumerate(KO_DP) if re.search(s0, p['t'])), None)
    if i0 is None: sys.exit('--ko-skip 시작을 찾지 못함: ' + s0)
    i1 = next((i for i, p in enumerate(KO_DP) if i > i0 and s1 and re.search(s1, p['t'])), len(KO_DP))
    print('짝짓기에서 뺀 한국어 문단', i1 - i0, ':', KO_DP[i0]['key'], '…', KO_DP[i1 - 1]['key'])
    KO_DP = KO_DP[:i0] + KO_DP[i1:]
# 손으로 '짝 없음'으로 정한 문단(--pin "열쇠+…=")은 짝짓기 전에 뺌 — 뒤에서 빼면 그 문단이 둘레 문장을 밀어냄 (2026-11-17 DL-0012 검수)
_nopin = {k for x in A.pin if x.endswith('=') for k in x[:-1].split('+') if k}
if _nopin: KO_DP = [p for p in KO_DP if p['key'] not in _nopin]
if A.ko_none: KO_DP = [p for p in KO_DP if not any(re.search(r, p['t']) for r in A.ko_none)]
SPL = re.compile(r'(?<=[.?!。…။])(?:[”’"\')\]]*)\s+|\n')
if A.my_comma: SPL = re.compile(r'(?<=[.?!。…။])(?:[”’"\')\]]*)\s+|\n|(?<=၊)\s+')
if A.ko_join: SPL = re.compile(r'(?<=[.?!。…။])(?:[”’"\')\]]*)(?:\[\^[^\]]+\])*\s+|(?<=[^.][.?!][’”])(?=[가-힣])(?!(?:라고|라는|라며|라면서|라든가|라든지|라거나|라도|란|이라|하고|하며|하면서|하는|하니|하자|하여|해서|했|한다|할|고\b|고 |는|며|면서|와|과|도|만|까지|에서|에게|로|을|를|이|가|의))|\n')   # 문장 끝 뒤 각주 번호('…것이다.’[^88] 비구들이여') 뒤에서도 나눔 (DL-0022)
MYEND = re.compile(r'(တယ်|ဘူး|ပဲ|ပေါ့|လဲ|တုန်း|နော်|လေ|တာ|မယ်|သလား|ကော|ရော|ရဲ့|တဲ့|ပါ|သည်)၊$')


def sents(t, lang):
    """문장 나누기: [(시작, 끝)] — 글자 자리(원래 글 기준)"""
    if lang == 'en' and A.en_semi:
        out = []
        for a, b in _sents(t, lang):
            x = a
            for m in re.finditer(r';\s+|(?<=[?!.’”])—(?=[“‘])', t[a:b]):   # 쌍반점, 말하는 이가 바뀌는 '…?”—“…'
                y = a + m.end()
                mn_ = 40 if m.group(0).startswith(';') else 12   # 짧은 조각('with contact as condition, feeling;')은 나누지 않음
                if m.group(0).startswith(';') and len(re.findall(r';\s+with\b', t[a:b])) >= 4 and re.search(r'\bwith\b', t[x:a + m.start()]) and re.match(r'with\b', t[y:]): continue   # 연기 공식 사슬('with X as condition, Y; with Y …')은 한 문장으로 — 한국어판은 늘 한 문장
                if len(t[x:a + m.start()].strip()) >= mn_ and len(t[y:b].strip()) >= mn_: out.append((x, a + m.start() + (1 if m.group(0).startswith(';') else 0))); x = y
            out.append((x, b))
        return out
    return _sents(t, lang)


def _sents(t, lang):
    out = __sents(t, lang)
    if lang == 'en':
        for k in range(1, len(out)):
            a, b = out[k]
            if t[a:a + 1] in '’”' and t[a + 1:a + 2] == ' ' and out[k - 1][1] <= a:
                out[k - 1] = (out[k - 1][0], a + 1); out[k] = (a + 2, b)
    return out


def __sents(t, lang):
    out = []; a = 0
    for m in SPL.finditer(t):
        b = m.start() if t[m.start()] == '\n' else m.end()
        seg = t[a:b].strip()
        if A.my_comma and t[m.start() - 1:m.start()] == '၊' and (lang == 'ko' or not MYEND.search(t[a:m.start()])): continue
        if m.group(0) != '\n' and re.fullmatch(r'(## |%% )?[0-9IVXⅠ-Ⅻ]+\.', seg): continue
        if lang == 'ko' and A.ko_dots and m.group(0) != '\n':
            pre = t[a:m.start()].rstrip('”’"\')]')
            if re.search(r'(\.\.\.|…)$', pre) and not re.search(r'[다요까죠네오라][”’"\']*\s*(\.\.\.|…)$', pre): continue   # '1. 제목'·'I. 제목' 의 번호 뒤에서는 나누지 않음
        if lang == 'en' and m.group(0) != '\n':
            # 'e.g. ' 'i.e. ' 'Mr. ' 'U. ' 같은 약어 뒤나 다음 글자가 소문자면 나누지 않음
            nx = t[m.end():m.end() + 1]
            if re.search(r'\b(e\.g|i\.e|etc|Mr|Mrs|Dr|cf|vs|No|v|vv|pp)\.$', t[a:m.start() + 1].strip()) or (nx and nx.islower()): continue
            # 경전·책 약어('B. Dict.' 'Vis. M.' 'S. XXII.' 'Dhp.' 'Comm.') 뒤, 생략 점('. . .')에서는 나누지 않음 (DL-0015)
            if re.search(r'(?:^|[\s(])(?:[A-Z]|B|Vis|Dict|Comm|Dhp|Snp|Ud|Fund|Vol|ff|lit|Cf|[IVX]+)\.$', t[a:m.start() + 1].strip()) and not re.search(r'[a-z]{3}\.$', t[a:m.start() + 1].strip()[-5:]) or nx == '.': continue
        # 따옴표 뒤 이음말('…존재한다.’ 거나', '…’ 라고')은 앞 문장에 (DL-0022, --ko-join)
        if lang == 'ko' and A.ko_join and m.group(0) != '\n' and re.match(r'(거나|라고|하고|라는|이라고|라며|하면서)[\s,]', t[m.end():m.end() + 6]): continue
        # '“알았습니다. 세존이시여”' 처럼 짧은 대답 뒤 부르는 말(…이여·…시여·…님)은 같은 문장 (DL-0022, --ko-join)
        if lang == 'ko' and A.ko_join and m.group(0) != '\n' and len(seg) <= 12 and re.match(r'\s*[가-힣 ]{1,12}(이여|시여|님)[.?!”’"\'』」]', t[m.end() - 1:m.end() + 20]): continue
        # 로마자 이름 첫 글자('호너I. B. Horner')에서는 나누지 않음 — 한국어 문장 속 로마자 머리글자 (DL-0019)
        if lang == 'ko' and m.group(0) != '\n' and re.search(r'(?:^|[^A-Za-z])[A-Z]\.$', t[a:m.start() + 1].strip()) and re.match(r'\s*[A-Z]', t[m.end() - 1:m.end() + 2]): continue
        if (lang == 'en' or re.fullmatch(r'[’”\'"\s.…]+', seg)) and seg and not re.search(r'\w', seg) and out: out[-1] = (out[-1][0], a + len(t[a:b].rstrip())); a = m.end(); continue   # 점만 있는 조각은 앞 문장에
        if lang == 'en' and re.fullmatch(r'(\[\d+\]\s*)+', seg): continue   # PTS 쪽 표시 '[169]' 만 있는 조각은 다음 문장과 함께 (DL-0022)
        if seg: out.append((a + len(t[a:b]) - len(t[a:b].lstrip()), a + len(t[a:b].rstrip())))
        a = m.end()
    if out and (lang == 'en' and re.fullmatch(r'(\[\d+\]\s*)+', t[a:].strip()) or re.fullmatch(r'[’”\'"\s.…]+', t[a:].strip())): out[-1] = (out[-1][0], len(t.rstrip())); return out
    if t[a:].strip(): out.append((a + len(t[a:]) - len(t[a:].lstrip()), len(t.rstrip())))
    return out


KS = []   # (para index, a, b, text, [이어진 조각 (para index, a, b)…])
for i, p in enumerate(KO_DP):
    for n_, (a, b) in enumerate(sents(p['t'], 'ko')):
        tx = plain(p['t'][a:b]).strip()
        if not tx: continue
        if A.ko_join and n_ == 0 and KS and KS[-1][0] == i - 1 and KO_DP[i - 1]['key'].split(':')[0] != p['key'].split(':')[0] \
           and not re.search(r'[.?!。…”’"\')\]]$', KS[-1][3]) and not re.match(r'(## |%% |\^\^ |:: |>> )', p['t']) and not re.match(r'(## |%% |\^\^ |:: |>> )', KO_DP[i - 1]['t']):
            q = KS[-1]; KS[-1] = (q[0], q[1], q[2], q[3] + ' ' + tx, q[4] + [(i, a, b)]); continue   # 쪽이 넘어가며 갈라진 문장은 앞 문장에
        KS.append((i, a, b, tx, []))
ORDER = list(range(len(ORIG))); MOVED = {}
def _oi(x):
    """원서 문단: 번호, '@글 첫머리', 같은 첫머리가 여럿이면 '@글 첫머리~N'(N 번째, 1부터 — DL-0015 'CONJOINED WITH OTHER FACTORS')"""
    if not x.startswith('@'): return int(x)
    m = re.match(r'@(.*)~(\d+)$', x)
    t, n = (m.group(1), int(m.group(2))) if m else (x[1:], 1)
    L = [i for i, p in enumerate(ORIG) if p['t'].startswith(t)]
    L = [i for i in L if ORIG[i]['k'] != 'toc'] or L   # 원서 차례 줄보다 본문 제목을 먼저
    return L[n - 1]
for mv in A.move:
    ab, c = mv.split('>'); a, b = map(int, ab.split('-')); c = _oi(c)
    blk = [i for i in ORDER if a <= i <= b]; rest = [i for i in ORDER if not a <= i <= b]
    k = rest.index(c); ORDER = rest[:k] + blk + rest[k:]
    for i in blk: MOVED[i] = (a, b)
ES = []; EDROP = []
# 원서 쪽만 '짝 없음'(--pin "=원서 번호 또는 @글 첫머리+…")도 짝짓기 전에 뺌 — 한국어판에 없는 원서 풀이 글이 둘레 문장을 끌어당기지 않게 (DL-0015)
_onopin = {_oi(k) for x in A.pin if x.startswith('=') for k in x[1:].split('+') if k}
for i in ORDER:
    p = ORIG[i]
    if i in _onopin: continue
    if p['k'] in ('toc', 'gl', 'pq', 'fn', 'sep', 'cite'): continue      # 원서 차례 쪽·용어 풀이·인용 상자(본문을 크게 다시 실은 것)·여백 출처(cite)는 문장 짝짓기에서 뺌 (한국어 차례도 %% 라 뺌)
    for a, b in sents(p['t'], 'en'):
        if not plain(p['t'][a:b]).strip(): continue
        if any(re.match(r, plain(p['t'][a:b]).strip()) for r in A.en_drop): EDROP.append((i, a, b)); continue
        ES.append((i, a, b, plain(p['t'][a:b]).strip()))
# --seg: 경계 앞뒤 문장은 서로 짝짓지 않음 (뜻 비슷함을 -1 로)
def _kt(k): return tuple(map(int, k.split(':')))
_SEG = []
for sg in A.seg:
    kk, oo = sg.split('=')
    kk = kk.split('+')[0]; oi = _oi(oo.split('+')[0])   # 여러 문단 핀('A+B=@x+@y')이면 첫 문단이 경계
    _SEG.append((_kt(kk), oi))
KSg = [sum(1 for k, _ in _SEG if _kt(KO_DP[x[0]]['key']) >= k) for x in KS]
_POS = {i: n for n, i in enumerate(ORDER)}   # --move 뒤의 원서 순서
ESg = [sum(1 for _, o in _SEG if _POS[x[0]] >= _POS[o]) for x in ES]
print('한국어 문단', len(KO), '문장', len(KS), '/ 원서 문단', len(ORIG), '문장', len(ES))

# ---------- 뜻 벡터 ----------
from sentence_transformers import SentenceTransformer
cache = os.path.join(REPO, 'tools/out/parallel', f'{A.book}.{A.lang}.emb.npz')
model = SentenceTransformer('sentence-transformers/LaBSE')
def enc(xs): return model.encode(xs, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
key = str(hash(tuple(x[3] for x in KS)) ^ hash(tuple(x[3] for x in ES)))
if os.path.exists(cache) and np.load(cache)['key'] == key:
    z = np.load(cache); KE, EE = z['ko'], z['en']
else:
    KE, EE = enc([x[3] for x in KS]), enc([x[3] for x in ES])
    np.savez(cache, ko=KE, en=EE, key=key)
N, M = len(KS), len(ES)
S = KE @ EE.T
if _SEG: S[np.array(KSg)[:, None] != np.array(ESg)[None, :]] = -1.0
KB = {k: float(v) for k, v in (x.split('=') for x in A.kind_base)}
PEN = np.array([KB.get(ORIG[x[0]]['k'], 0.0) for x in ES]) if ES else np.zeros(0)
S1 = S - A.base - PEN[None, :]   # 1단계(대강의 길)용

# ---------- 1단계: 대강의 길(1:1·건너뛰기)로 띠 찾기 ----------
SK = 0.05
D = np.full((N + 1, M + 1), -1e9); D[0, :] = -SK * np.arange(M + 1); D[:, 0] = -SK * np.arange(N + 1)
for i in range(1, N + 1):
    row = D[i]; prev = D[i - 1]; s = S1[i - 1]
    diag = prev[:-1] + s; up = prev[1:] - SK
    best = np.maximum(diag, up)
    # 왼쪽(원서 건너뛰기)은 차례로
    for j in range(1, M + 1):
        v = best[j - 1]; l = row[j - 1] - SK
        row[j] = v if v > l else l
path = []; i, j = N, M
while i > 0 and j > 0:
    if abs(D[i, j] - (D[i - 1, j - 1] + S1[i - 1, j - 1])) < 1e-9: path.append((i - 1, j - 1)); i -= 1; j -= 1
    elif abs(D[i, j] - (D[i - 1, j] - SK)) < 1e-9: i -= 1
    else: j -= 1
center = np.zeros(N, dtype=int)
pts = sorted(path)
if pts:
    pi = np.array([p[0] for p in pts]); pj = np.array([p[1] for p in pts])
    center = np.interp(np.arange(N), pi, pj).astype(int)
W = A.band

# ---------- 2단계: 묶음까지 허용한 짝짓기 (띠 안에서) ----------
BEADS = [(1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (3, 1), (1, 0), (0, 1)]
if A.en_semi: BEADS += [(1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (4, 1), (5, 1), (2, 3), (3, 2)]   # 긴 목록('abstention from … is wholesome;' ×10)을 한국어 한 문장에   # 쌍반점으로 잘게 나눈 원서 조각 여럿 ↔ 한국어 한 문장 (DL-0022)
cK = np.vstack([np.zeros(KE.shape[1]), np.cumsum(KE, 0)]); cE = np.vstack([np.zeros(EE.shape[1]), np.cumsum(EE, 0)])
def sim(i0, i1, j0, j1):
    if _SEG and i1 > i0 and j1 > j0 and len({KSg[i0], KSg[i1 - 1], ESg[j0], ESg[j1 - 1]}) > 1: return -1.0
    a = cK[i1] - cK[i0]; b = cE[j1] - cE[j0]
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
SKIP = -0.15; MERGE = 0.10
INF = -1e18
V = {}; B = {}
V[(0, 0)] = 0.0
def lo(i): return max(0, center[min(i, N - 1)] - W) if N else 0
def hi(i): return min(M, center[min(i, N - 1)] + W) if N else M
for i in range(0, N + 1):
    for j in range(lo(i), hi(i) + 1):
        if (i, j) == (0, 0): continue
        best = INF; bb = None
        for a, b in BEADS:
            pi, pj = i - a, j - b
            if pi < 0 or pj < 0 or (pi, pj) not in V: continue
            if a and b:
                sc = (sim(pi, i, pj, j) - A.base - (PEN[pj:j].max() if j > pj and KB else 0.0)) * (a + b) / 2 - MERGE * (max(a, b) - 1 + (a > 1 and b > 1))
            else:
                sc = SKIP
            v = V[(pi, pj)] + sc
            if v > best: best, bb = v, (a, b)
        if bb is not None: V[(i, j)] = best; B[(i, j)] = bb
end = (N, M) if (N, M) in V else max((k for k in V if k[0] == N), key=lambda k: V[k])
beads = []; i, j = end
while (i, j) != (0, 0):
    a, b = B[(i, j)]; beads.append((i - a, i, j - b, j)); i, j = i - a, j - b
beads.reverse()

# ---------- 문단 묶음 ----------
groups = []   # [set ko paras, set en paras, beads]
for i0, i1, j0, j1 in beads:
    kp = {KS[k][0] for k in range(i0, i1)} | {x[0] for k in range(i0, i1) for x in KS[k][4]}; ep = {ES[k][0] for k in range(j0, j1)}
    if groups and ((kp & groups[-1][0]) or (ep & groups[-1][1])):
        groups[-1][0] |= kp; groups[-1][1] |= ep; groups[-1][2].append((i0, i1, j0, j1))
    else: groups.append([set(kp), set(ep), [(i0, i1, j0, j1)]])
# 문단 사이 빈틈(짝 없는 문단)도 묶음 순서를 지키게 정리
out = []
for kp, ep, bs in groups:
    sent = []
    for i0, i1, j0, j1 in bs:
        sc = round(sim(i0, i1, j0, j1), 3) if i1 > i0 and j1 > j0 else None
        sent.append({'ko': [y for k in range(i0, i1) for y in [[KO_DP[KS[k][0]]['key'], KS[k][1], KS[k][2]]] + [[KO_DP[x[0]]['key'], x[1], x[2]] for x in KS[k][4]]],
                     'or': [[ES[k][0], ES[k][1], ES[k][2]] for k in range(j0, j1)], **({'sc': sc} if sc is not None else {})})
    out.append({'ko': [KO_DP[k]['key'] for k in sorted(kp)], 'or': sorted(ep),
                'ka': plain(KO_DP[min(kp)]['t'])[:24] if kp else '', 's': sent})
# 손으로 정한 짝(--pin): 그 문단들을 다른 묶음에서 빼고 따로 한 묶음으로
for pin in A.pin:
    kk, oo = pin.split('=')
    kk = [x for x in kk.split('+') if x]
    def oidx(x):   # 원서 문단: 번호 또는 '@글 첫머리'
        return _oi(x)
    oo = [oidx(x) for x in oo.split('+') if x]
    for g in out:
        g['ko'] = [k for k in g['ko'] if k not in kk]; g['or'] = [o for o in g['or'] if o not in oo]
        for st in g['s']:
            st['ko'] = [x for x in st['ko'] if x[0] not in kk]; st['or'] = [x for x in st['or'] if x[0] not in oo]
        g['s'] = [st for st in g['s'] if st['ko'] or st['or']]
    out[:] = [g for g in out if g['ko']]   # 한국어 문단이 빠진 묶음의 원서 문단은 짝 없음
    if kk and oo:
        KOT = {f'{n}:{i}': q for n, (lab, _, txt) in enumerate(pages, 1) for i, q in enumerate(paras(txt))}   # 그림 문단(속표지 그림 등)도 손으로 짝지을 수 있게
        out.append({'ko': kk, 'or': oo, 'ka': plain(KOT[kk[0]])[:24], 'pin': 1,
                    's': [{'ko': [[k, 0, len(KOT[k])] for k in kk], 'or': [[o, 0, len(ORIG[o]['t'])] for o in oo]}]})
out.sort(key=lambda g: tuple(map(int, g['ko'][0].split(':'))) if g['ko'] else (1e9, 0))
# 같은 한국어 문단이 두 묶음에 걸치면 하나로 합침 (화면은 한국어 문단마다 묶음 하나)
_m = []
for g in out:
    if _m and set(g['ko']) & set(_m[-1]['ko']) and not g.get('pin') and not _m[-1].get('pin'):
        h = _m[-1]; h['ko'] = sorted(set(h['ko']) | set(g['ko']), key=lambda k: tuple(map(int, k.split(':'))))
        h['or'] = sorted(set(h['or']) | set(g['or'])); h['s'] += g['s']
    else: _m.append(g)
out[:] = _m
if A.en_semi:   # 쌍반점으로 나눈 원서 조각이 짝 없이 남으면 같은 원서 문단의 이웃 문장 짝에 붙임 (DL-0022)
    for g in out:
        S = g['s']; k = 0
        while k < len(S):
            st = S[k]
            if not st['ko'] and st['or']:
                o = st['or'][0][0]
                if k + 1 < len(S) and S[k + 1]['ko'] and S[k + 1]['or'] and S[k + 1]['or'][0][0] == o:
                    S[k + 1]['or'] = st['or'] + S[k + 1]['or']; del S[k]; continue
                if k > 0 and S[k - 1]['ko'] and S[k - 1]['or'] and S[k - 1]['or'][-1][0] == st['or'][-1][0]:
                    S[k - 1]['or'] = S[k - 1]['or'] + st['or']; del S[k]; continue
            k += 1
for i, a, b in EDROP:   # --en-drop: 같은 원서 문단의 앞 문장 바로 뒤(없으면 뒤 문장 앞)에 원서만 있는 줄로
    for g in out:
        if i not in g['or']: continue
        S = g['s']; at = None
        for k, st in enumerate(S):
            if any(o == i and y <= a for o, x, y in st['or']): at = k + 1
        if at is None: at = next((k for k, st in enumerate(S) if any(o == i for o, _, _ in st['or'])), len(S))
        S.insert(at, {'ko': [], 'or': [[i, a, b]]}); break
# 여백 출처(cite, DL-0015 'M. 26'): 바로 다음 원서 문단이 든 묶음 앞에 붙임 (문단 나란히 보기에서 출처가 보이게)
_og = {o: g for g in out if not g.get('toc') for o in g['or']}
for i, p in enumerate(ORIG):
    if p['k'] != 'cite': continue
    j = i + 1
    while j < len(ORIG) and ORIG[j]['k'] == 'cite': j += 1
    if j < len(ORIG) and j in _og and i not in _og[j]['or']: _og[j]['or'] = sorted(set(_og[j]['or']) | {i})
for g in out:   # --move 로 옮긴 원서 문단과 짝지은 묶음: 순서가 다르다는 메모
    if g['or'] and not g.get('pin') and all(o in MOVED for o in g['or']):
        o = ORIG[g['or'][0]]
        g['note'] = f"원서와 순서가 다릅니다 — 원서 {o['pg']}쪽" + (f"(PDF {o['pdf']}쪽)" if o.get('pdf') and o['pdf'] != o['pg'] else '') + "에 있는 글입니다."
# 차례(--toc): 쪽 번호를 뺀 제목 줄끼리 순서를 지키며 짝지음 → 묶음 하나(toc: 1) — tools/parallel/toc.py
if A.toc:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from toc import toc_group, put_toc
    put_toc(out, toc_group(T['body'], ORIG, out, enc, book=A.book))
# 용어 풀이: 한국어 '낱말(roman) : 풀이' ↔ 원서 낱말
import unicodedata
def rk(x): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFD', x).encode('ascii', 'ignore').decode().lower())
EG = {}
for i, p in enumerate(ORIG):
    if p['k'] == 'gl': EG.setdefault(rk(re.sub(r'\(also see[^)]*\)', '', p['term'])), i)
gl_ok = gl_no = 0; cur = None; frag = []
for p in KO_GL:
    if A.gl_nl and re.fullmatch(r'\*\*[^\n*]+\*\*', p['t']) and '(' not in p['t'].replace('(**', ''):   # 쪽 끝에서 잘린 낱말 조각 → 다음 문단과 함께
        frag.append(p); continue
    if A.gl_nl and re.fullmatch(r'\*\*[^\n*]+\(\*\*', p['t']): frag.append(p); continue      # '**실라(**' + '**sīla)**'
    pt = ''.join(plain(f['t']) for f in frag) + plain(p['t'])
    m3 = (re.match(r'[^\n(]*?\(([^)]*[a-zāīūṃṅñṭḍṇḷ][^)]*)\)\s*\n', pt) or re.match(r'[^\n(]+\n[a-z]\) ([a-zāīūṃṅñṭḍṇḷ]+)\n', pt)) if A.gl_nl else None
    m = m3 or re.match(r'[^\n(]*?\(([^)]*[a-zāīūṃṅñṭḍṇḷ][^)]*)\)\s*:', plain(p['t'])) or re.match(r'[^\n\[]*?\[([^\]]*[a-zāīūṃṅñṭḍṇḷ][^\]]*)\]\s*\n', plain(p['t']))   # '낱말(roman) : 풀이' 또는 '낱말[roman]⏎풀이'(DL-0013)
    if m:
        j = None
        for c in m.group(1).split(','):          # 'pāramī, pāramita' 처럼 여러 표기
            j = EG.get(rk(c))
            if j is not None: break
        if j is None:                             # 'satipaṭṭhāna' ↔ 'Satipatthāna Sutta', 오자 'somassna' ↔ 'somanassa'
            import difflib
            k0 = rk(m.group(1).split(',')[0])
            j = next((v for k, v in EG.items() if k.startswith(k0) and len(k0) >= 6), None)
            if j is None:
                best = max(EG, key=lambda k: difflib.SequenceMatcher(None, k, k0).ratio())
                if difflib.SequenceMatcher(None, best, k0).ratio() >= 0.8: j = EG[best]
        if j is None: gl_no += 1; print('  용어 못 찾음:', m.group(1)); cur = None; frag = []; continue
        gl_ok += 1
        ps = frag + [p]; frag = []
        cur = {'ko': [x['key'] for x in ps], 'or': [j], 'ka': pt[:24], 'gl': 1, 's': [{'ko': [[x['key'], 0, len(x['t'])] for x in ps], 'or': [[j, 0, len(ORIG[j]['t'])]]}]}
        out.append(cur)
    elif cur is not None:      # 풀이가 다음 문단(①②③, 다음 쪽)으로 이어짐
        for x in frag + [p]: cur['ko'].append(x['key']); cur['s'][0]['ko'].append([x['key'], 0, len(x['t'])])
        frag = []
print('용어 풀이 짝', gl_ok, '못 찾음', gl_no)
# ---------- 각주 짝 (운영자 요청, 2026-11-17): 한국어 각주([^n]:, [역주] 는 뺌) ↔ 원서 각주('fn' 문단) — 뜻 벡터 + 순서 지키는 짝짓기 ----------
FN = {}; fn_rep = []
KF = [(m.group(1), m.group(2).strip()) for m in re.finditer(r'^\[\^([^\]]+)\]:\s*(.*(?:\n(?!\[\^|===).*)*)', body, flags=re.M)]
YK = {n for n, t in KF if t.lstrip('*').startswith('[역주]')}   # 역자 각주: 원서 각주를 풀어 쓴 것도 있어 뜻이 아주 가까울 때만 짝
EF = [(i, re.sub(r'^\[\^[^\]]+\]:\s*', '', p['t'])) for i, p in enumerate(ORIG) if p['k'] == 'fn']
if KF and EF:
    kfe, efe = enc([plain(t)[:400] for _, t in KF]), enc([t[:400] for _, t in EF])
    FS = kfe @ efe.T
    n1, m1 = len(KF), len(EF); G = np.zeros((n1 + 1, m1 + 1)); BK = {}
    for i in range(n1 + 1):
        for j in range(m1 + 1):
            if i == 0 and j == 0: continue
            c = []
            if i and j: c.append((G[i - 1, j - 1] + FS[i - 1, j - 1] - (0.6 if KF[i - 1][0] in YK else 0.2), 'd'))
            if i: c.append((G[i - 1, j], 'u'))
            if j: c.append((G[i, j - 1], 'l'))
            G[i, j], BK[(i, j)] = max(c)
    i, j = n1, m1
    while i or j:
        b = BK[(i, j)]
        if b == 'd':
            FN[KF[i - 1][0]] = EF[j - 1][0]; fn_rep.append((KF[i - 1], EF[j - 1], float(FS[i - 1, j - 1]))); i -= 1; j -= 1
        elif b == 'u': i -= 1
        else: j -= 1
    fn_rep.reverse()
    for x in A.fnpin:   # 손으로 정한 각주 짝
        kn, en = x.split('=')
        if not en: FN.pop(kn, None); fn_rep = [r for r in fn_rep if r[0][0] != kn]; continue   # "14=" 한국어 각주 14 는 짝 없음
        ei = next(i for i, t in EF if ORIG[i]['t'].startswith(f'[^{en}]:'))
        if not kn: FN = {k: v for k, v in FN.items() if v != ei}; fn_rep = [r for r in fn_rep if r[1][0] != ei]; continue   # "=3" 원서 각주 3 은 짝 없음
        FN = {k: v for k, v in FN.items() if v != ei}; FN[kn] = ei
        fn_rep = [r for r in fn_rep if r[1][0] != ei and r[0][0] != kn] + [((kn, dict(KF)[kn]), (ei, ORIG[ei]['t']), 1.0)]
    print('각주 짝', len(FN), '/ 한국어 각주', len(KF), '(역주', len(YK), ') / 원서 각주', len(EF))
scores = [s['sc'] for g in out if not g.get('toc') for s in g['s'] if 'sc' in s]
res = {'book': A.book, 'lang': A.lang, 'title': A.title, 'by': A.by, 'source': A.source,
       'made': datetime.date.today().isoformat(), 'method': 'LaBSE 문장 뜻 비교 + 순서 지키는 짝짓기(1:1·1:2·2:1·2:2·1:3·3:1·건너뛰기)',
       'note': '짝 자료: groups[].ko = 한국어 문단 열쇠 "쪽 순번:문단 순번"(content/texts 본문 기준), or = 원서 문단 번호, s = 문장 짝 [문단 열쇠·번호, 시작 글자, 끝 글자], sc = 뜻 비슷함(0~1)',
       'orig': [{'pg': p['pg'], 'k': p['k'], 't': p['t'], **({'pdf': p['pdf']} if p.get('pdf') else {})} for p in ORIG], 'groups': out, **({'fn': FN} if FN else {})}
os.makedirs(os.path.join(REPO, 'content/parallel'), exist_ok=True)
json.dump(res, open(os.path.join(REPO, 'content/parallel', f'{A.book}.{A.lang}.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
low = [(g, s) for g in out for s in g['s'] if not g.get('gl') and not g.get('toc') and not g.get('pin') and (s.get('sc', 1) < 0.5 or 'sc' not in s)]   # 용어 풀이·차례·손으로 정한 짝은 확인 목록에서 뺌
print('문장 짝', sum(len(g['s']) for g in out), '문단 묶음', len(out), '평균 점수', round(float(np.mean(scores)), 3),
      '0.5 아래·건너뜀', len(low))
KOI = {x['key']: x for x in KO}
rep = os.path.join(REPO, 'tools/out/parallel', f'{A.book}.{A.lang}.report.txt')
with open(rep, 'w') as f:
    for g, s in low:
        kt = ' / '.join(KOI[k]['t'][a:b] for k, a, b in s['ko'])
        et = ' / '.join(ORIG[p]['t'][a:b] for p, a, b in s['or'])
        f.write(f"[{s.get('sc', '건너뜀')}] {g['ko'][:1]} 원서 {g['or'][:1]}\n  한: {kt[:200]}\n  원: {et[:200]}\n")
if fn_rep or (KF and EF):
    with open(rep, 'a') as f:
        f.write('\n===== 각주 짝 =====\n')
        got = {k[0] for k, _, _ in fn_rep}; gote = {e[0] for _, e, _ in fn_rep}
        for (kn, kt), (ei, et), sc in fn_rep: f.write(f"[{sc:.2f}] 한 {kn} ↔ 원 {ORIG[ei]['t'][:6]}  {plain(kt)[:60]} || {et[:60]}\n")
        for kn, kt in KF:
            if kn not in got and kn not in YK: f.write(f"[짝 없음] 한국어 각주 {kn}: {plain(kt)[:80]}\n")
        for ei, et in EF:
            if ei not in gote: f.write(f"[짝 없음] 원서 각주 {ORIG[ei]['t'][:80]}\n")
print('확인 목록 →', rep)
