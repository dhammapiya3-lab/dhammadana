"""DL-0022『붓다의 깨달음』(맛지마 니까야 선집, 빅쿠 케마짜라 옮김) 원서 대조 — 영어 원서 글 → 원서 문단 목록
(운영자 요청, 2026-11-19·20)

원서: Bhikkhu Ñāṇamoli & Bhikkhu Bodhi, The Middle Length Discourses of the Buddha (Wisdom Publications).
한국어판에 실린 26개 경만 옮김(한국어판 차례 순서).
 ① 19개 경 — SuttaCentral 이 공개한 보디 스님 번역(2009판, CC BY-NC-ND 3.0) html_text/en/pli/sutta/mn/mnN.html 의 글
    그대로(운영자 요청: '이걸 가지고 작업하고 pdf 파일은 비교 검수용으로만'). 바꾼 것: PTS 쪽 표시 mn.i.7 → [7]
    (인쇄본 모양), 게송 줄 바꿈은 줄 바꿈으로. SuttaCentral 은 인쇄본 단락 번호 대신 자기 번호(SC n)를 써서 단락
    번호는 글에 넣지 않고, 스캔본 글자 인식 글에서 찾은 인쇄본 단락 첫머리를 'sec' 로만 적어 짝짓기 기준점으로 씀.
 ② SuttaCentral 에 없는 7개 경(MN 10·21·39·61·105·112·152) — 스캔본 PDF(majjhima-nikaya.pdf, 1995 초판, 글자층 없음,
    책 쪽 = PDF 쪽 + OFF[경])을 글자 인식해 쪽 그림과 대조해 고친 tools/parallel/dl0022_en/NNNN.txt (NNNN = PDF 쪽):
      '@ 책쪽 pdf PDF쪽 mn 경번호' 첫 줄, '## ' 제목, 빈 줄 = 문단 나눔, '+ ' 앞 쪽 문단에 이어짐, '+- ' 낱말 가운데에서 이어짐,
      게송 줄은 ' / ' 없이 줄마다(문단 안 줄 바꿈은 '\\' 로 끝나는 줄).
    본문의 미주 번호(위첨자)는 넣지 않음 — ①과 같게.
 ③ 미주 — 보디 스님의 미주 가운데 한국어판 각주로 옮긴 것: tools/parallel/dl0022_notes.txt
    ('# MN 경번호' 줄 아래 '번호<TAB>글', 스캔본 미주 쪽 글자 인식을 쪽 그림과 대조해 고친 것) → 'fn' 문단.
쪽(pg)은 인쇄본 쪽 — ① 은 스캔본 글자 인식 글(작업 공간)에서 단락 자리를 찾아 붙임.

  python3 tools/parallel/en_dl0022.py [SuttaCentral mn 폴더]  → tools/out/parallel/DL-0022.en.paras.json
"""
import os, re, sys, json, glob, html, unicodedata
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SC = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/suttacentral/sc-data/html_text/en/pli/sutta/mn'
SRC = os.path.join(REPO, 'tools/parallel/dl0022_en')
DRAFT = os.environ.get('DL22_DRAFT', '/home/claude/work/dl0022/draft')   # 19개 경의 스캔본 글자 인식 글(단락 번호·쪽 찾기용, 저장소 밖)
OUT = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(OUT, exist_ok=True)
ORDER = [26, 4, 36, 95, 135, 41, 61, 21, 63, 29, 27, 39, 19, 20, 7, 8, 2, 112, 152, 105, 10, 118, 9, 38, 148, 149]
OCRED = {10, 21, 39, 61, 105, 112, 152}
# 숫따센트럴 머리에는 빠알리 경 이름이 없어 인쇄본(MLDB)처럼 적음
PALI = {26: 'Ariyapariyesana Sutta', 4: 'Bhayabherava Sutta', 36: 'Mahāsaccaka Sutta', 95: 'Caṅkī Sutta',
        135: 'Cūḷakammavibhaṅga Sutta', 41: 'Sāleyyaka Sutta', 63: 'Cūḷamālukya Sutta', 29: 'Mahāsāropama Sutta',
        27: 'Cūḷahatthipadopama Sutta', 19: 'Dvedhāvitakka Sutta', 20: 'Vitakkasaṇṭhāna Sutta', 7: 'Vatthūpama Sutta',
        8: 'Sallekha Sutta', 2: 'Sabbāsava Sutta', 118: 'Ānāpānasati Sutta', 9: 'Sammādiṭṭhi Sutta',
        38: 'Mahātaṇhāsaṅkhaya Sutta', 148: 'Chachakka Sutta', 149: 'Mahāsaḷāyatanika Sutta'}
# ONLY_SC=1 이면 숫따센트럴에 있는 19개 경만 (7개 경·미주는 허락 확인 전)
if os.environ.get('ONLY_SC'): ORDER = [m for m in ORDER if m not in OCRED]
# 인쇄본 쪽 = PDF 쪽 + OFF[경] — 스캔본 PDF 가 몇 쪽씩 건너뛰어 경마다 다름(쪽 위 머리글 숫자로 확인)
OFF = {26: 9, 4: 6, 36: 11, 95: 21, 135: 27, 41: 13, 61: 17, 21: 9, 63: 17, 29: 9, 27: 9, 39: 11, 19: 8, 20: 8,
       7: 6, 8: 6, 2: 6, 112: 25, 152: 28, 105: 23, 10: 6, 118: 25, 9: 6, 38: 11, 148: 28, 149: 28}


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c)).lower()


def words(s):
    return re.findall(r'[a-z]+', fold(s))


def read_pages(d, mn):
    """쪽 파일 → [(pdf, 책쪽, 글)]"""
    out = []
    for f in glob.glob(os.path.join(d, '[0-9][0-9][0-9][0-9].txt')):
        L = open(f, encoding='utf-8').read().rstrip('\n').split('\n')
        m = re.match(r'@ (\S+) pdf (\d+) mn (\d+)', L[0])
        if int(m.group(3)) == mn: out.append((int(m.group(2)), m.group(1), '\n'.join(L[1:]).strip()))
    return sorted(out)


def page_paras(pages):
    """쪽 파일 → 문단 [{pg,pdf,k,t}]"""
    out = []
    for pdf, pg, body in pages:
        for para in re.split(r'\n\s*\n', body):
            lines = [x.strip() for x in para.split('\n') if x.strip()]
            if not lines: continue
            t = ''
            for x in lines:
                if t.endswith('\\'): t = t[:-1].rstrip() + '\n' + x
                elif t: t += ' ' + x
                else: t = x
            if t.startswith('+- '): out[-1]['t'] += t[3:]; continue
            if t.startswith('+ '): out[-1]['t'] += ' ' + t[2:]; continue
            k = 'h' if t.startswith('## ') else 'p'
            out.append({'pg': pg, 'pdf': str(pdf), 'k': k, 't': t[3:] if k == 'h' else t})
    return out


def inline(s):
    s = re.sub(r"<a class='ref sc'[^>]*>.*?</a>", '', s)
    s = re.sub(r"<a class='ref pts-vp-pli'[^>]*>mn\.[ivx]+\.(\d+)</a>", r'[\1]', s)
    s = re.sub(r'<br>\s*', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r' ?\n ?', '\n', s)
    return s.strip()


def sc_paras(mn):
    t = open(os.path.join(SC, f'mn{mn}.html'), encoding='utf-8').read()
    t = t.split('<footer>')[0]
    head = re.search(r'<header>(.*?)</header>', t, re.S).group(1)
    lis = [inline(x) for x in re.findall(r'<li[^>]*>(.*?)</li>', head, re.S)]
    h1 = inline(re.search(r'<h1>(.*?)</h1>', head, re.S).group(1))
    out = [{'k': 'h', 't': f'{mn} {PALI[mn]}'}, {'k': 'h', 't': re.sub(r'^\d+\.\s*', '', h1)}]
    body = t.split('</header>')[1]
    for m in re.finditer(r'<(h2|h3|p)( [^>]*)?>(.*?)</\1>', body, re.S):
        x = inline(m.group(3))
        if not x: continue
        out.append({'k': 'h' if m.group(1) != 'p' else 'p', 't': x})
    return out


def locate(paras, draft):
    """스캔본 글자 인식 글과 SuttaCentral 글을 낱말로 맞대어(difflib) 원서 문단마다 쪽을 붙이고,
    인쇄본 단락 첫머리('N. ')가 SuttaCentral 문단 첫머리와 맞으면 그 문단에 sec=N (화면에는 보이지 않음 — 짝짓기 기준점)"""
    import difflib
    D = []   # 초안 낱말 (낱말, 쪽, pdf, 단락 번호)
    for p in draft:
        m = re.match(r'\W*(\d+)\s*[.,]\s', p['t'])
        num = int(m.group(1)) if (m and p['k'] == 'p') else None
        for j, w in enumerate(words(p['t'])): D.append((w, p['pg'], p['pdf'], num if j == 0 else None))
    S = []   # SuttaCentral 낱말 (낱말, 문단 번호, 문단 안 순서)
    for i, p in enumerate(paras):
        for j, w in enumerate(words(p['t'])): S.append((w, i, j))
    sm = difflib.SequenceMatcher(None, [x[0] for x in S], [x[0] for x in D], autojunk=False)
    s2d = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n): s2d[a + k] = b + k
    d2s = {v: k for k, v in s2d.items()}
    first = {}
    for k, (w, i, j) in enumerate(S):
        if i not in first: first[i] = k
    # 쪽
    lastpg = (D[0][1], D[0][2]) if D else ('', '')
    for i, p in enumerate(paras):
        k = first.get(i)
        if k is not None:
            for kk in range(k, k + 30):
                if kk in s2d: lastpg = (D[s2d[kk]][1], D[s2d[kk]][2]); break
        p['pg'], p['pdf'] = lastpg
    # 단락 번호
    nums = []; miss = []
    for di, (w, pg, pdf, num) in enumerate(D):
        if num is None: continue
        # 초안 단락 첫 낱말 둘레에서 SuttaCentral 낱말 자리 찾기
        k = None
        for dd in range(di, di + 4):
            if dd in d2s: k = d2s[dd] - (dd - di); break
        if k is None or k < 0 or k >= len(S): miss.append(num); continue
        i = S[k][1]
        if S[k][2] > 2 or paras[i]['k'] != 'p' or re.match(r'\d+\. ', paras[i]['t']): miss.append(num); continue
        paras[i]['sec'] = num; nums.append((i, num))
    # 순서가 맞지 않는 번호(글자 인식 잡음)는 뺌 — 문단 순서와 번호 순서가 함께 늘어나는 가장 긴 줄만 남김
    best = []
    for i, n in nums:
        cand = [b for b in best if b[-1][0] < i and b[-1][1] < n]
        best.append((max(cand, key=len) if cand else []) + [(i, n)])
    keep = set(max(best, key=len)) if best else set()
    for i, n in nums:
        if (i, n) not in keep: paras[i].pop('sec', None); miss.append(n)
    return miss


notes = {}
NF = os.environ.get('DL22_NOTES') or os.path.join(REPO, 'tools/parallel/dl0022_notes.txt')
if os.path.exists(NF):
    cur = None
    for line in open(NF, encoding='utf-8'):
        line = line.rstrip('\n')
        m = re.match(r'# MN (\d+)(?:\s+pdf\s+(\d+))?', line)
        if m: cur = int(m.group(1)); continue
        if not line.strip() or cur is None: continue
        m = re.match(r'(\d+)\t(\S+)\t(.*)', line)   # 번호<TAB>책쪽<TAB>글
        if m: notes.setdefault(cur, []).append((m.group(1), m.group(2), m.group(3)))
        elif notes.get(cur): n, pg, t = notes[cur][-1]; notes[cur][-1] = (n, pg, t + '\n' + line)

orig = []; report = []
for mn in ORDER:
    if mn in OCRED:
        P = page_paras(read_pages(SRC, mn))
    else:
        P = sc_paras(mn)
        miss = locate(P, page_paras(read_pages(DRAFT, mn)))
        if miss: report.append(f'MN {mn}: 단락 번호를 찾지 못함·뺌 {sorted(miss)}')
        P[0]['pg'], P[0]['pdf'] = P[2]['pg'], P[2]['pdf']; P[1]['pg'], P[1]['pdf'] = P[2]['pg'], P[2]['pdf']
        for p in P: p.pop('_at', None)
    for p in P:
        p['mn'] = mn
        if p.get('pdf'): p['pg'] = str(int(p['pdf']) + OFF[mn])
    orig += P
    for n, pg, t in notes.get(mn, []):
        orig.append({'pg': pg, 'k': 'fn', 'mn': mn, 't': f'[^{mn}.{n}]: {t}'})
json.dump(orig, open(os.path.join(OUT, 'DL-0022.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
print('원서 문단', len(orig), '/ 경', len(ORDER), '/ 미주', sum(len(v) for v in notes.values()))
print('\n'.join(report))
