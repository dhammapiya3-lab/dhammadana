"""『위빠싸나 성자 아짠문』(DL-0040, 아짠 마하 부와 엮음 · 김열권 옮김, 불광출판사 초판 2000 — 마하위빠사나 명상원 법보시 PDF 2016)
PDF → content/texts/DL-0040.json
  python3 tools/pdf2text_dl0040.py 책.pdf

한글(Hwp 2020)에서 Hancom PDF 로 내보낸 A4 310쪽. 쪽 아래 '- N -' = PDF 쪽 번호 = 쪽 이름 (차례의 쪽 번호도 같음).
- PDF 1쪽은 앞표지 그림이라 넣지 않음(책 표지가 따로 있음). 6쪽은 빈 쪽(쪽 표시만).
- 2 속표지, 3~5 역자 소개·알림(줄 모양이 제각각이라 인쇄된 줄을 손으로 이어 적고 PDF 글자와 같은지 대조),
  7~8 역자 서문(끝 서명 3줄 >> ), 9~13 차례(인쇄된 줄 그대로 %% — '‖ 16' 쪽 번호도 그대로),
  14~15 '프라 아짠 문(Phra Acharn Mun, 1870～1950)', 16~302 본문 1~6장, 303~308 보충주, 308 아래 출판 알림(판권지), 309~310 명상원 안내.
- 장 표지 쪽(16·46·124·154·265·280): 20pt 장 이름 + 짧은 줄 글(줄마다 줄 바꿈) — 장 이름은 표지 글 그대로
  (장 첫머리라 읽기 화면에서는 위 큰 장 제목 하나로 보임), 다음 쪽의 18pt '제N장 …' 줄은 ## .
- 소제목: 인쇄된 차례 항목과 같은 본문 줄(12.9~15.9pt 한 줄) → ## (읽기 목차 소제목).
- 본문 Haansoft Batang 12pt, 왼쪽 85pt. 문단 첫 줄은 들여 씀(x≥90 또는 줄 앞 빈칸). 오른쪽 끝(500 넘게)까지 찬 줄은
  다음 줄과 이어 붙임(줄 끝 빈칸 글자가 있으면 띄움, 없으면 붙임 — 한글 파일의 글자 단위 줄바꿈).
  들여 쓴 묶음(x≈110, 17~18쪽 꿈 이야기)은 ++ , 줄 앞 빈칸이 많은(5칸 넘게) 짧은 줄 묶음(게송)은 ++ 줄마다,
  302쪽 끝 날짜 줄(빈칸 38칸)은 >> .
- 쪽이 넘어가는 문단은 앞 쪽 문단에 이어 붙임(DL-0037 처럼) — 그 문단의 각주 풀이도 앞 쪽으로.
- 각주: 본문 9pt 'N)' → [^N], 쪽 아래 각주(T4·T5·T6 글꼴 10~11pt, 'N) …') → [^N]: …. 이 글꼴은 낱말 사이 빈칸이
  글자로 없어 글자 사이 자리(2pt 넘게 벌어짐)로 빈칸을 되살림. 끝까지 찬 각주 줄을 이을 때 빈칸은 kiwi 로 정함(WRAP).
  6장 286·293·294쪽의 '(역자 주)' 각주(본문 자리에 '__________' 아래 10pt, 번호 40·41·42 가 앞 각주 번호와 겹침)는
  [^*40]·[^*41]·[^*42] (DL-0032 처럼), '__________' 줄은 뺌.
- 보충주(303~308): '주N) …'·'※ …' 줄 → ## , ㉠ 항목 줄은 줄마다, 둘째 줄부터 빈칸으로 들여 쓴 줄은 앞 줄에 이어 붙임.
- 글자는 PDF 그대로(겹친 빈칸·'\\50,000' 도).
"""
import sys, re, json, os, collections, difflib
import fitz

pdf = sys.argv[1]
HWP = sys.argv[2] if len(sys.argv) > 2 else None
BK, ED = 'DL-0040', '초판'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = fitz.open(pdf)
log = collections.Counter()
WRAPLOG = []
KIWI = None


def is_t(f): return re.fullmatch(r'T\d+', f) is not None


def lines(n):
    out = []
    for b in d[n - 1].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            ch = [(c, s) for s in l['spans'] for c in s['chars']]
            if not ''.join(c['c'] for c, _ in ch).strip(): continue
            out.append(dict(ch=ch, x0=l['bbox'][0], y0=l['bbox'][1], x1=l['bbox'][2]))
    out.sort(key=lambda r: (round(r['y0']), r['x0']))
    m = []
    for r in out:
        if m and abs(m[-1]['y0'] - r['y0']) < 3:
            m[-1]['ch'] += r['ch']; m[-1]['x1'] = max(m[-1]['x1'], r['x1']); m[-1]['x0'] = min(m[-1]['x0'], r['x0'])
        else: m.append(r)
    for r in m:
        r['ch'].sort(key=lambda cs: cs[0]['origin'][0])
        r['t'] = text(r, n)
        big = [s['size'] for c, s in r['ch'] if c['c'].strip() and not isref(s)]
        r['size'] = max(big) if big else 0
        r['font'] = next((s['font'] for c, s in r['ch'] if c['c'].strip()), '')
        r['lead'] = len(r['t']) - len(r['t'].lstrip(' '))
        r['plain'] = re.sub(r'\[\^\*?\d+\]', '', r['t'])
    return [r for r in m if not re.fullmatch(r'\s*-\s*\d+\s*-\s*', r['t'])]


def isref(s): return s['size'] < 9.5 and not is_t(s['font'])


def text(r, n):
    """글자 → 줄 글. 작은 'N)' 는 [^N] (286~294쪽 8pt 는 [^*N]). T 글꼴은 벌어진 자리에 빈칸 —
    양쪽 맞춤으로 글자 사이를 고르게 벌린 줄(34쪽 각주 23 '5khandha')이 있어 그 줄의 보통 글자 사이(가운데 값)보다 2.5pt 넘게 벌어진 곳만"""
    # 34쪽 각주 23 처럼 글자마다 좁은 빈칸 글자(양쪽 맞춤으로 벌린 자리, 보통 빈칸은 글자 크기의 0.55배)가 끼어 있는 줄 — 보이지 않는 빈칸이라 뺌(글자 자리로 판단)
    ch = [(c, s) for c, s in r['ch'] if not (c['c'] == ' ' and is_t(s['font']) and c['bbox'][2] - c['bbox'][0] < 0.3 * s['size'])]
    if len(ch) != len(r['ch']): log['폭 없는 빈칸 글자 뺌'] += len(r['ch']) - len(ch)
    gaps = []
    for (a, sa), (c, sc) in zip(ch, ch[1:]):
        if a['c'] != ' ' and c['c'] != ' ' and (is_t(sa['font']) or is_t(sc['font'])) and not isref(sa) and not isref(sc):
            gaps.append(c['bbox'][0] - a['bbox'][2])
    med = sorted(gaps)[len(gaps) // 2] if gaps else 0
    o = ''; prev = None; ref = ''; refsz = 0
    def flush():
        nonlocal o, ref
        if ref:
            num = re.sub(r'\D', '', ref)
            assert num, (n, ref)
            o += f'[^*{num}]' if refsz < 8.5 else f'[^{num}]'
            log['각주 번호'] += 1; ref = ''
    for c, s in ch:
        t = c['c']
        if isref(s) and t.strip() or (ref and isref(s)):
            if not ref: refsz = s['size']
            ref += t; prev = (c, s); continue
        flush()
        if prev is not None and t != ' ' and not o.endswith(' ') and (is_t(s['font']) or is_t(prev[1]['font'])):
            if c['bbox'][0] - prev[0]['bbox'][2] > max(2.0, med + 2.5): o += ' '; log['글자 자리로 넣은 빈칸'] += 1
        o += t; prev = (c, s)
    flush()
    return o


def wrap_sep(a, b, hwp=True):
    h = hwp_sep(a, b) if hwp else None
    r = h if h is not None else _wrap_sep(a, b); JLOG.append((CURP, a[-18:], '·' if r else '|', b[:18])); return r


JLOG = []; CURP = 0; SHORT = []


def _wrap_sep(a, b):
    """끝까지 찬 각주 줄을 이을 때 빈칸 — 줄 끝 빈칸이 글자로 없으므로 kiwi 로 고름 (DL-0036 wrap_sep 와 같은 생각)"""
    global KIWI
    if re.search(r'[.?!,:;]$', a): return ' '
    if b.startswith('(') and re.search(r'[가-힣]$', a): return ''          # '적멸|(열반)'·'성위|(聖位)'
    if re.match(r'[‘“]', b) and re.search(r'[가-힣A-Za-z0-9]$', a): return ' '
    if re.match(r'[①-⑳㉠-㉻·․]', b) or re.search(r'[·․]$', a): return ' '   # 목록 '지내기 ⑬눕지'·'피부 · 살'
    if a.endswith(')') and not re.match(r'[을를이가은는의에과와도로라]', b): return ' '
    if re.search(r'[A-Za-zāīūṃṅñṭḍṇḷ]$', a) and re.match(r'[가-힣]', b): return ' '
    if re.search(r'[가-힣]$', a) and re.match(r'\d', b): return ' '            # '경행 길은  |  20보정도'
    if re.search(r'[가-힣]$', a) and re.match(r'[가-힣]', b):
        fa = re.search(r'[가-힣]+$', a).group(); fb = re.match(r'[가-힣]+', b).group()
        jn = len(re.findall(re.escape(fa + fb), CORPUS)); spn = len(re.findall(re.escape(fa + ' ' + fb), CORPUS))
        if jn != spn and max(jn, spn) >= 1:
            WRAPLOG.append(('책', a[-15:], b[:15], jn, spn)); return '' if jn > spn else ' '
        if KIWI is None:
            from kiwipiepy import Kiwi
            KIWI = Kiwi()
        sc = lambda s: KIWI.analyze(s)[0][1]
        tail = re.sub(r'\[\^\*?\d+\]', '', a)[-20:]; head = b[:20]
        dd = sc(tail + head) - sc(tail + ' ' + head)
        if abs(dd) <= 1:
            sp = KIWI.space(tail + head, reset_whitespace=False); k = 0; ia = len(tail.replace(' ', ''))
            for i, ch in enumerate(sp):
                if ch != ' ': k += 1
                if k == ia: dd = -1 if (i + 1 < len(sp) and sp[i + 1] == ' ') else 1; break
        WRAPLOG.append(('kiwi', a[-15:], b[:15], round(dd, 2)))
        return '' if dd > 0 else ' '
    return ''


ALL = {n: lines(n) for n in range(1, d.page_count + 1)}

# 한글 파일(있으면): 줄을 이을 때 빈칸을 넣을지는 한글 파일 글의 빈칸으로 정함 — PDF 는 줄 끝 빈칸이 글자로 남지 않는
# 곳이 있음(113쪽 '모아졌을 때|그와' 는 한글 파일도 붙어 있음, 172쪽 '믿었다.|그리고' 는 띄어 있음)
HS, HSP, HSN, HNL = '', set(), {}, set()
if HWP:
    import subprocess
    raw = subprocess.run(['hwp5txt', HWP], capture_output=True, text=True).stdout
    buf = []; sp = 0; nl = False
    for ch in raw:
        if ch.isspace():
            sp += 1; nl = nl or ch == '\n'; continue
        if sp and buf:
            HSP.add(len(buf)); HSN[len(buf)] = sp
            if nl: HNL.add(len(buf))
        sp = 0; nl = False; buf.append(ch)
    HS = ''.join(buf)


def hwp_sep(a, b, multi_ok=True):
    """한글 파일에서 a 끝 + b 첫머리를 찾아 그 사이에 빈칸이 있는지 — 한 곳만 찾히거나 찾힌 곳이 모두 같을 때만"""
    if not HS: return None
    nz = lambda x: re.sub(r'\s|\[\^\*?\d+\]', '', x)
    for ka in (12, 20, 30):
        A = nz(a)[-ka:]; Bk = nz(b)[:12]
        if not A or not Bk: return None
        pos = [m.start() for m in re.finditer(re.escape(A + Bk), HS)]
        if not pos: continue
        flags = {(p + len(A)) in HSP for p in pos}
        if len(flags) == 1:
            if all((p + len(A)) in HNL for p in pos):   # 한글 파일에서 '엔터' — 같은 문단 안 줄 바꿈
                log['줄 잇기 — 한글 파일의 엔터라 줄 바꿈'] += 1; return '\n'
            many = max(HSN.get(p + len(A), 0) for p in pos)
            if many >= 2 and not multi_ok: return None   # 한글 파일도 빈칸 여러 칸(줄 맞추기용) — 판단에 맡김
            log['줄 잇기 빈칸 — 한글 파일대로'] += 1; return ' ' if flags.pop() else ''
    log['줄 잇기 빈칸 — 한글 파일에서 못 찾음'] += 1; NOTFOUND.append((CURP, a[-15:], b[:15]))
    return None


NOTFOUND = []
# 책 안에서 줄 가운데에 쓰인 꼴(붙임/띄움)을 셀 글 — 본문·각주의 줄들
CORPUS = '\n'.join(r['plain'] for n in ALL for r in ALL[n])

# ---------- 인쇄된 차례 (PDF 9~13) ----------
TOCP = []    # (단계, 제목, 쪽)
toc_rows = []; prev_y = None
for n in range(9, 14):
    for r in ALL[n]:
        t = r['t'].strip()
        if re.fullmatch(r'차\s+례', t): continue
        gap = r['y0'] - prev_y if prev_y is not None and n == toc_rows[-1][0] else 0
        prev_y = r['y0']
        lv = 1 if r['x0'] > 110 else 0
        toc_rows.append((n, lv, t, gap))
        m = re.match(r'(.*?)\s*[‖∥]\s*(\d+)$', t)
        TOCP.append((lv, (m.group(1) if m else t).strip(), int(m.group(2)) if m else None))
toc_shown = []
for k, (n, lv, t, gap) in enumerate(toc_rows):
    if k and gap > 30: toc_shown.append('~')
    toc_shown.append(('- ' if lv else '') + t)

PAGES = []
images = []
chapters = []   # (제목, 쪽 순번, 문단 순번)
subs = []
FN = {}         # 번호 → 글


def newpage(lab):
    P = {'lab': lab, 'paras': [], 'fns': []}; PAGES.append(P); return P


def same(a, b):
    k = lambda s: re.sub(r'[\s\-–·․‘’“”\'"().,?!]', '', s)
    return k(a) == k(b)


def check_hand(n, paras, skip=()):
    """손으로 적은 쪽 글이 PDF 글자와 같은지 (빈칸·표시 빼고)"""
    k = lambda s: re.sub(r'\s|\^\^|::|\+\+|>>', '', s)
    pdf_t = k(''.join(r['t'] for r in ALL[n] if r['t'].strip() not in skip))
    mine = k(''.join(paras))
    assert pdf_t == mine, (n, pdf_t, mine)
    log['손으로 이은 쪽 대조 같음'] += 1


# ---------- 앞쪽 ----------
P = newpage('2쪽'); chapters.append(('속표지', 0, 0))
P['paras'] = ['^^ 위빠싸나 성자', '^^ 아짠문', ':: 아짠 마하 부와 엮음·김열권 옮김', ':: 불광출판사에서 출판(2000년 4월 초판)',
              ':: 마하위빠사나 명상원']
check_hand(2, P['paras'])

P = newpage('3쪽'); chapters.append(('역자 소개', 1, 0))
P['paras'] = [
    '역자 不遠 金烈權',
    '약력 고려대 경영대학원MBA석사, 10년간 선사들 지도하에 화두수행, 1990년 미얀마출가 마하시선원에서 한국인으로 최초 미안마비구계 받고 태국, 말레이시아, 인도 등에서 위빠싸나 수행. 특히 태국 붓다다사 선원, 태국 위벡아좀, 미얀마 쉐우민 선원, 모곡선원의 지도자들로부터 위빠싸나 사사 받음. 그 후 한국 산사에서 대승관법 수행과 티벳 수행 3년 후 경전에 근거한 위빠싸나 수행 중.',
    '현재 마하 위빠싸나 명상/ 위빠싸나 붓다선원장',
    '++ 네이버 카페 http://cafe.naver.com/panna48\n다음카페 위빠싸나 붓다선원 http://cafe.daum.net/bulwon\nBAND모임 http://band.us/@mahavipassana',
    'E-Mail : vipassanakim@hanmail.net',
    '수행처 서울 종로구 삼봉로81 두산위브 836호\n매주  월, 화, 토 수행, 강의 중\n매월 사찰에서 7일 집중 수행 진행 중',
    ':: 수행 참여 하실 분 언제나 환영합니다.\n초보자도 환영합니다.']
check_hand(3, P['paras'])
P = newpage('4쪽')
P['paras'] = [
    '저서 위빠싸나 1·2, 보면 사라진다, 있는 그대로 보는 지혜',
    '역서 붓다의 후예, 위빠싸나 선사들 · 붓다의 호흡법, 아나빠나삿띠 · 붓도 위빠싸나 · 마음으로 숨쉬는 붓다 등',
    '논문 핵심감정과 사념처 · 남방위빠싸나와 대승위빠싸나 · 또 다른 선, 위파사나의 이해 · 기업에서 마음경영, 창조, 마음챙김',
    '강의경력 불교TV - 체험! 붓다의 수행법, 위빠싸나 12회\n유나방송, 동국대학교, 서울 불교 대학원 대학교, 전남대 심리학과, 창원대 심리대학원, 영산대학원, 위덕대학 등에서 특강, 목사님들 수행지도 3박4일 3차례\n심리교수와 정신과의사모임지도, 호두마을 등',
    '1. 아짠문 수행 3개월과정, 통신강좌 이용 가능함.(자율보시      )',
    '2. (사)한국명상지도자협회 명상지도사 자격증 수여\n70시간+통신강좌(6개월,수행자료+ 매주 폰 인터뷰)',
    '3. 후원 보시금: 우리은행 : 129-081058-02-402\n예 금 주 : 김열권']
check_hand(4, P['paras'])
P = newpage('5쪽')
P['paras'] = [':: *위 책자의 내용 사용 시\n출처를 밝히고 이용 바랍니다.', ':: 마하 위빠사나 수행 MAP']
check_hand(5, P['paras'])
newpage('6쪽')

# ---------- 본문 (7~8, 14~308) ----------
COVERS = {16, 46, 124, 154, 265, 280}
FULL = 500


def lastP():
    return next((Q for Q in reversed(PAGES[:-1]) if Q['paras']), None)


def joinl(a, t):
    """끝까지 찬 줄 a 와 다음 줄 t 잇기 — 줄 끝 빈칸 한 칸이면 띄움, 없으면 붙임.
    빈칸을 여러 칸 쳐서 줄을 넘긴 곳(보충주 '벗어  |난다'·'아         |직', 앞 줄 끝 빈칸 2칸 넘게나 다음 줄 앞 빈칸)은
    낱말 가운데일 수 있어 책 안 꼴·kiwi 로 정함 (WRAP)"""
    tr = len(a) - len(a.rstrip(' ')); ld = len(t) - len(t.lstrip(' '))
    if tr >= 2 or ld >= 2:
        log['빈칸 여러 칸 줄 잇기(판단)'] += 1
        h = hwp_sep(a.rstrip(' '), t.lstrip(' '), multi_ok=False)   # 한글 파일에 빈칸 한 칸이면 띄움, 여러 칸(보기 맞추기용)이면 판단
        return a.rstrip(' ') + (h if h is not None else wrap_sep(a.rstrip(' '), t.lstrip(' '), hwp=False)) + t.lstrip(' ')
    h = hwp_sep(a, t)
    if h is not None:
        if (h == ' ') != a.endswith(' '): HWPDIFF.append((CURP, a[-15:], repr(h), t[:15]))
        return a.rstrip(' ') + h + (t.lstrip(' ') if h == '\n' else t)
    if not a.endswith(' ') and re.search(r'[.?!,;:]["”’]?$', a) and re.match(r'[가-힣A-Za-z0-9“‘(]', t):
        log['문장부호 뒤 줄 잇기 빈칸'] += 1; JLOG.append((CURP, a[-18:], '·', t[:18])); return a + ' ' + t
    if re.search(r'[가-힣]$', a) and re.match(r'[가-힣]', t): MID.append((CURP, a[-12:], t[:12]))
    return a + t


HWPDIFF = []


MID = []


def add(P, t, kind='B'):
    P['paras'].append(t); P.setdefault('kinds', {})[len(P['paras']) - 1] = kind
    return len(P['paras']) - 1


# 차례 항목(소제목)을 쪽마다
want = collections.defaultdict(list)
for lv, t, pg in TOCP:
    if lv == 1 and pg: want[pg].append(t)
found_sub = set()
prev_end = None   # 앞 쪽 마지막 본문 줄 (이어지는 문단인지)
pend_fn = None    # 앞 쪽 마지막 각주 번호 (다음 쪽으로 넘어간 각주)
pend_full = False
cur_ch = None
for n in list(range(7, 9)) + list(range(14, 309)):
    L = ALL[n]; CURP = n
    P = newpage(f'{n}쪽'); pi = len(PAGES) - 1
    if n == 7:
        chapters.append(('역자 서문', pi, 0)); add(P, L[0]['t'].strip(), 'H'); L = L[1:]
    if n == 14:
        chapters.append(('프라 아짠 문(Phra Acharn Mun, 1870～1950)', pi, 0)); add(P, L[0]['t'].strip(), 'H'); L = L[1:]
    if n in COVERS:
        title = L[0]['t'].strip(); chapters.append((title, pi, 0)); add(P, '^^ ' + title, 'H')
        t = ''
        for r in L[1:]:
            seg = r['t'].strip()
            t = (t + seg if r is L[1] else (t + (hwp_sep(t, seg) or '') + seg if prevr['x1'] > FULL else t + '\n' + seg)); prevr = r
        add(P, t, 'C'); prev_end = None; continue
    if n == 303:
        chapters.append(('보충주', pi, 0))
    body = []; fns = []; infn = False
    for r in L:
        if re.fullmatch(r'_+', r['t'].strip()): infn = True; continue
        if is_t(r['font']) or (infn and r['size'] < 11): fns.append(r)   # '____' 아래 10pt 각주 — 294쪽은 그 뒤에 12pt 본문이 이어짐
        else: body.append(r)
    if n == 308:   # 아래쪽 출판 알림 → 판권지
        tail = [r for r in body if r['y0'] > 590]; body = [r for r in body if r['y0'] <= 590]
    cur = None; prev = None
    for idx, r in enumerate(body):
        t = r['t']; s = t.strip()
        # 장 제목 줄 (18pt '제N장 …')
        if r['size'] >= 17.5:
            add(P, '## ' + s, 'H'); cur = None; prev = r; continue
        if n == 303 and s == '보 충 주':
            add(P, s, 'H'); cur = None; prev = r; continue
        # 소제목: 인쇄된 차례 항목과 같은 줄
        cand = [w for w in want.get(n, []) + want.get(n - 1, []) + want.get(n + 1, []) if same(w, s)]
        if not cand and r['size'] >= 12.5 and len(s) < 60:
            kk = lambda x: re.sub(r'[\W_一-鿿]', '', x).lower()
            best = max(want.get(n, []), key=lambda w: difflib.SequenceMatcher(None, kk(w), kk(s)).ratio(), default=None)
            if best and difflib.SequenceMatcher(None, kk(best), kk(s)).ratio() >= 0.75: cand = [best]; log['소제목(글자가 조금 다름)'] += 1
        if cand:
            found_sub.add((n, cand[0])); j = add(P, '## ' + s, 'H'); subs.append((s, pi, j)); cur = None; prev = r
            log['소제목'] += 1; continue
        if n >= 303 and (re.match(r'주\s?\d+(,\d+)?\)', s) or s.startswith('※')) and r['size'] >= 11.5:
            add(P, '## ' + s, 'H'); cur = None; prev = r; log['보충주 제목'] += 1; continue
        if n == 8 and r['font'].startswith('MDSol'):
            add(P, '>> ' + s, 'C'); cur = None; prev = r; continue
        if r['lead'] >= 30:
            add(P, '>> ' + s, 'C'); cur = None; prev = r; log['날짜 줄 >>'] += 1; continue
        block = 105 <= r['x0'] < 130
        verse = r['lead'] >= 5 and n < 303
        # 172쪽처럼 낱말 단위로 줄을 바꾼 곳은 오른쪽 끝이 들쭉날쭉 — 455 넘게 찬 줄 다음의 들여 쓰지 않은 줄은 같은 문단
        full = lambda q: q['x1'] > (480 if 105 <= q['x0'] < 130 else 500 if q['size'] < 11 else 455)   # 보충주(10pt)는 오른쪽 끝 510 안팎
        start = r['lead'] > 0 or r['x0'] >= 90
        if n >= 303 and re.match(r'\s*(\d+\)|[㉠-㉻①-⑳*※→↓])', t): start = True
        elif n >= 303 and prev is not None and (full(prev) or r['lead'] >= 4):   # 보충주: 표시(㉠·①·→ 등) 없이 들여 쓴 줄은 앞 줄에 이어짐
            start = False   # 보충주: 둘째 줄부터 들여 쓴 줄(항목 글자 자리에 맞춰 들여 씀)
        if block and prev is not None and 105 <= prev['x0'] < 130 and r['lead'] == 0:
            start = False
        if block and prev is None and r['lead'] == 0 and prev_end is not None and prev_end.get('block'):
            start = False   # 들여 쓴 묶음(꿈 이야기 등)이 쪽을 넘어 이어짐 (17→18쪽)
        if verse:
            if cur is not None and P['kinds'].get(cur) == 'V' and prev is not None and prev['lead'] >= 5:
                P['paras'][cur] += '\n' + s
            else:
                cur = add(P, s, 'V')
            prev = r; continue
        if cur is None and prev is None and not start and prev_end is not None and prev_end['full'] and lastP():
            LP = lastP(); LP['paras'][-1] = joinl(LP['paras'][-1], t)
            cur = 'prev'; prev = r; log['쪽을 넘어 이어 붙인 문단'] += 1
            # 이 줄의 각주 번호 풀이도 앞 쪽으로
            for m in re.finditer(r'\[\^(\*?\d+)\]', t): LP.setdefault('move', []).append(m.group(1))
            continue
        if cur is not None and prev is not None and not start and full(prev):
            if cur == 'prev':
                LP = lastP(); LP['paras'][-1] = joinl(LP['paras'][-1], t)
                for m in re.finditer(r'\[\^(\*?\d+)\]', t): LP.setdefault('move', []).append(m.group(1))
            else: P['paras'][cur] = joinl(P['paras'][cur], t)
            log['이음'] += 1; prev = r; continue
        # 따옴표로 끝난 짧은 줄 다음 '…라고/고/하고 …' 로 이어지는 줄(엔터로 줄을 바꾼 곳)은 같은 문단 안 줄 바꿈 (43·39·64·259·275쪽)
        if cur is not None and cur != 'prev' and prev is not None and not start and not full(prev) \
                and (re.search(r'[”’]\s*$', P['paras'][cur]) and re.match(r'(라고|고|하고|하며|라며|하면서|라는)\b', t)
                     or not re.search(r'[.?!”’):]\s*$', P['paras'][cur])
                     or n >= 303 and r['lead'] >= 4):   # 보충주 항목 글자 자리에 맞춰 들여 쓴 줄 (306쪽 '㉣ 풍대 … 등. ⏎ 4대에 관한 …')   # 문장이 끝나지 않은 짧은 줄 (39쪽 '우두머리 원숭이는 ⏎ “콕! (저기!)”')
            P['paras'][cur] = P['paras'][cur].rstrip(' ') + '\n' + t.lstrip(' '); log['따옴표 뒤 엔터 줄(같은 문단 줄 바꿈)'] += 1; prev = r; continue
        if cur is not None and cur != 'prev' and prev is not None and not start and not full(prev):
            log['짧은 줄 뒤 들여 쓰지 않은 줄(새 문단)'] += 1; SHORT.append((n, round(prev['x1']), P['paras'][cur][-25:], t[:25]))
        cur = add(P, t.lstrip(' '), 'Q' if block else 'B'); prev = r
    if body:
        lb = body[-1]
        prev_end = dict(full=(lb['x1'] > (480 if 105 <= lb['x0'] < 130 else FULL)) and lb['lead'] < 5, block=105 <= lb['x0'] < 130)
    # 각주
    fprev = None
    for r in fns:
        t = r['t']; s = t.strip()
        m = re.match(r'(\d+)\)\s*', s) if is_t(r['font']) else None
        m2 = re.match(r'(\(역자 주\)\s*)\[\^\*(\d+)\]\s*', s)
        if m2:
            num = '*' + m2.group(2); FN[num] = m2.group(1) + s[m2.end():]; P['fns'].append(num); pend_fn = num; fprev = r; continue
        if m:
            num = m.group(1); FN[num] = s[m.end():]; P['fns'].append(num); pend_fn = num; fprev = r; continue
        # 이어지는 줄
        if fprev is None:
            log['다음 쪽으로 넘어간 각주'] += 1
            sep = wrap_sep(FN[pend_fn], s) if pend_full else '\n'
            FN[pend_fn] = FN[pend_fn] + sep + s
        elif fprev['x1'] > FULL and r['lead'] < 3:
            FN[pend_fn] = FN[pend_fn] + wrap_sep(FN[pend_fn], s) + s; log['각주 줄 이음'] += 1
        else:
            FN[pend_fn] = FN[pend_fn].rstrip(' ') + '\n' + s; log['각주 안 줄 바꿈'] += 1
        fprev = r
    if fns: pend_full = fns[-1]['x1'] > FULL
    if n == 308:
        P = newpage('308쪽'); chapters.append(('판권지', len(PAGES) - 1, 0))
        P['paras'] = [':: ' + tail[0]['t'].strip(), ':: ' + tail[1]['t'].strip(),
                      ':: ' + '\n'.join(r['t'].strip() for r in tail[2:])]
        check_hand(308, [r['t'] for r in ALL[308] if r['y0'] <= 590] + P['paras'])
        log['판권지 쪽 표시 하나 더'] += 1

# ---------- 차례 (9~13) — 역자 서문(7~8) 뒤, 프라 아짠 문(14) 앞 ----------
toc_pages = []
for k, n in enumerate(range(9, 14)):
    toc_pages.append({'lab': f'{n}쪽', 'paras': (['차    례', '%% ' + '\n'.join(toc_shown)] if k == 0 else []), 'fns': []})
ins = next(i for i, Q in enumerate(PAGES) if Q['lab'] == '14쪽')
PAGES[ins:ins] = toc_pages
shift = len(toc_pages)
chapters = [(t, pi + shift if pi >= ins else pi, j) for t, pi, j in chapters]
subs = [(t, pi + shift if pi >= ins else pi, j) for t, pi, j in subs]
chapters.append(('차례', ins, 0))

# ---------- 뒤쪽 309~310 ----------
P = newpage('309쪽'); chapters.append(('마하 위빠싸나 명상원', len(PAGES) - 1, 0))
P['paras'] = [
    '^^ 마하 위빠싸나 명상원', '명상원장님 : vipassanakim@hanmail.net',
    '++ 네이버 카페 http://cafe.naver.com/panna48\n다음카페 위빠싸나 붓다선원 http://cafe.daum.net/bulwon\nBAND모임 http://band.us/@mahavipassana',
    '수행처 서울 종로구 삼봉로81 두산위브 836호\n매주  월, 화, 토 수행, 강의 중\n매월 사찰에서 7일 집중 수행 진행 중',
    ':: 수행 참여 하실 분 언제나 환영합니다.\n초보자도 환영 합니다.',
    '1.  3개월 과정, 통신강좌 이용 가능함. (월 \\50,000원)',
    '2. (사)한국명상지도자협회 명상지도사 자격증 수여\n총 \\ 200,000원\n70시간+통신강좌(6개월, 수행자료 +매주 폰 인터뷰)',
    '3. 후원 보시금: 우리은행 : 129-081058-02-402\n예 금 주 : 김열권']
check_hand(309, P['paras'])
P = newpage('310쪽')
P['paras'] = [':: *위 책자의 내용 사용 시\n출처를 밝히고 이용 바랍니다.', ':: 마하 위빠사나 명상원\n수행의 안내지도(MAP)', ':: (다음 장에서)']
check_hand(310, P['paras'])

# ---------- 마무리 ----------
# 각주 풀이를 번호가 있는 쪽으로 (쪽을 넘어 이어 붙인 문단)
where = {}
for i, Q in enumerate(PAGES):
    for p in Q['paras']:
        for m in re.finditer(r'\[\^(\*?\d+)\]', p): where.setdefault(m.group(1), i)
for i, Q in enumerate(PAGES): Q['fns'] = []
for f in FN:
    assert f in where, ('본문 번호 없는 각주', f)
    PAGES[where[f]]['fns'].append(f)
for Q in PAGES:
    kinds = Q.get('kinds', {})
    for j, p in enumerate(Q['paras']):
        p = re.sub(r'[ \t]+$', '', p, flags=re.M)
        if kinds.get(j) in ('Q', 'V'): p = '++ ' + p.strip()
        Q['paras'][j] = p
    for f in Q['fns']:
        Q['paras'].append(f'[^{f}]: ' + re.sub(r'[ \t]+(\n|$)', r'\1', FN[f]).strip())

chapters.sort(key=lambda x: (x[1], x[2]))
toc = []
for t, pi, j in chapters:
    toc.append(dict(title=t, page=pi + 1, sub=False, **({'at': t[:20]} if j > 0 else {})))
for t, pi, j in subs:
    toc.append(dict(title=t, page=pi + 1, sub=True, **({'at': t[:20]} if j > 0 else {})))
order = {(t, pi + 1): j for t, pi, j in chapters + subs}
toc.sort(key=lambda x: (x['page'], order.get((x['title'], x['page']), 0), x['sub']))

body = ''
for Q in PAGES:
    body += f"=== {Q['lab']} ===\n\n" + '\n\n'.join(Q['paras']) + '\n\n'
body = body.rstrip() + '\n'
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': [], 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
miss = [(pg, t) for lv, t, pg in TOCP if lv == 1 and pg and not any(t == w for _, w in found_sub)]
print(dict(log)); print('장', len(chapters), '소제목', len(subs), '각주', len(FN), '쪽', len(PAGES))
print('차례에 있는데 본문 소제목으로 못 찾은 것:', miss)
os.makedirs(os.path.join(REPO, 'tools/out'), exist_ok=True)
with open(os.path.join(REPO, 'tools/out/dl0040_wrap.tsv'), 'w') as f:
    for w in JLOG: f.write('\t'.join(map(str, w)) + '\n')
print('→', out)
for x in SHORT: print('짧은 줄', x)
for x in NOTFOUND: print('한글 파일에서 못 찾음', x)
for x in HWPDIFF: print('PDF 줄 끝 빈칸과 한글 파일이 다름', x)
json.dump(MID, open(os.path.join(REPO, 'tools/out/dl0040_mid.json'), 'w'), ensure_ascii=False)
