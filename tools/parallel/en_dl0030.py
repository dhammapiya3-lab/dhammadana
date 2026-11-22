"""『붓다의 일생』(DL-0030) 영어 원서 PDF → 원서 문단 목록 (운영자 요청, 2026-11-22)
  python3 tools/parallel/en_dl0030.py "The Life of the Buddha.pdf"  →  tools/out/parallel/DL-0030.en.paras.json
                                                                     + DL-0030.en.hyph.tsv (줄 끝 하이픈 판단 목록)

원서 판본 (판권 면 그대로): The Life of the Buddha according to the Pāli Canon, translation from the Pāli, selection of material
  and arrangement by Bhikkhu Ñāṇamoli, BPS Pariyatti Editions — ©1972, 1992 Buddhist Publication Society; Published by Buddhist
  Publication Society, Kandy, Sri Lanka, 1972, 1978, 1992; First BPS Pariyatti Edition, 2001 (Pariyatti eBook, InDesign PDF 400쪽,
  396×612pt). 쪽 이름: PDF 1~18 = 앞쪽(로마 숫자, PDF 쪽 = 로마 숫자), PDF 19~ = 인쇄 쪽 + 18 (쪽 아래 숫자 — 장 첫 쪽은 숫자가 없음).
- 글꼴: 이 PDF 는 옛 빠알리 글꼴 글자 자리(GaramondPali·HumanistPali)를 씀 → 글꼴마다 바로잡음(쪽 그림으로 확인):
  GaramondPali ± ā ² ī ³ ū µ ṭ º ṇ ¹ ḍ ½ ṃ ¼ ḷ ¾ Ā Ý Ṭ ð Ṇ, HumanistPali(머리글·제목) ¾ ā ð ṇ Þ ḍ ¿ ī (모두 큰 글자로 된 낱말 안에서는 큰 글자).
  작은 대문자(SC) 글꼴 글자는 PDF 글자 그대로('Narrator One', 'Ñāñamoli' 처럼 인쇄된 대로).
- 문단: 첫 줄 들여쓰기(60pt 넘게) = 새 문단, 54pt 줄 = 이어지는 줄. 쪽이 넘어가도 들여쓰지 않은 첫 줄은 앞 문단에 이어 붙임.
  게송(80~140pt 에서 시작하는 줄)은 인쇄된 줄마다 줄 바꿈('\n'), 줄 사이가 16pt 넘게 벌어지면 새 게송 문단.
  오른쪽에 붙은 경전 출처 줄(140pt 넘게서 시작, 'M. 26', 'Sn. 3:1')·서명 줄은 따로 문단 하나씩.
- 말하는 이 표시(Narrator One. · First Voice. · Chanter. 굵은 작은 대문자)는 '**…**' 로 감쌈(글자는 그대로) — 한국어판 §§…§§ 와 같은 자리.
- 장 제목(HumanistPali-Bold 14: 장 번호 줄 + 제목 줄)은 'h' 하나('1 THE BIRTH AND THE EARLY YEARS'), 12장 소제목(HumanistPali-Bold 10.9)도 'h'.
- 본문 속 주 번호(6.3pt 위첨자) → '[^장.번호]'(예 [^1.1]) — 원서 미주는 장마다 1부터 셈. 뒤쪽 NOTES(PDF 365~377) → 'fn' 문단 '[^장.번호]: 글'.
- 줄 끝 하이픈: 다음 줄이 소문자로 시작하면, 원서 안(줄 가운데)에서 하이픈 없이 붙여 쓴 낱말이 더 많으면 하이픈을 빼고 붙이고,
  하이픈 낱말이 더 많거나, 원서 안에 둘 다 없을 때 앞가지(self·non·well 등)이거나 붙인 꼴이 영어 낱말이 아니고 두 조각이 모두 영어 낱말이면
  ('word-meanings' — wordfreq 로 봄) 하이픈을 남김 — 판단 목록 hyph.tsv. 숨은 하이픈(U+00AD)은 빼고 붙임.
- 넣지 않는 쪽: 1~2(표지·Pariyatti 알림), 16~17(지도 — 글 없음), 378~392(List of Sources·Index), 396~400(다른 책 광고·Pariyatti 안내).
  12장 앞 차례 쪽(205쪽)도 'toc', 경 이름 소제목 줄 '(The Fire Sermon)' 은 'h'.
  3쪽 반표제·4쪽 속표지·5쪽 판권·6쪽 예경 게송·7쪽 차례(k toc)·393쪽 연표·394 저자 소개·395 저서 목록은 넣음, 8쪽 약어표는 'pq'.
"""
import sys, re, json, os, collections
import pymupdf
from wordfreq import zipf_frequency as zipf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = pymupdf.open(pdf)
SKIP = {1, 2, 16, 17} | set(range(378, 393)) | set(range(396, d.page_count + 1))
NOTES = range(365, 378)

GAR = str.maketrans({'±': 'ā', '²': 'ī', '³': 'ū', 'µ': 'ṭ', 'º': 'ṇ', '¹': 'ḍ', '½': 'ṃ', '¼': 'ḷ', '¾': 'Ā', 'Ý': 'Ṭ', 'ð': 'Ṇ', '': '❖'})
HUM = str.maketrans({'¾': 'ā', 'ð': 'ṇ', 'Þ': 'ḍ', '¿': 'ī', '±': 'ā'})


def fix(s, font):
    if font.startswith('Humanist'):
        t = s.translate(HUM)
        # 모두 큰 글자로 된 낱말 안의 바로잡은 글자는 큰 글자로 (AN¾THAPIðÞIKA → ANĀTHAPIṆḌIKA)
        return re.sub(r'\S+', lambda m: m.group(0).upper() if sum(c.isupper() for c in m.group(0)) >= 2 and not any(c in 'abcdefghijklmnopqrstuvwxyz' for c in m.group(0)) else m.group(0), t)
    if font.startswith('Garamond'): return s.translate(GAR)
    return s


def roman(n):
    out = ''
    for v, r in ((10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')):
        while n >= v: out += r; n -= v
    return out


# ---------- 1. 줄 모으기 ----------
LINES = []   # (pn, pg, line dict)
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP: continue
    pg = roman(pn) if pn <= 18 else str(pn - 18)
    for b in d[i].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'] != '']
            if not ''.join(s['text'] for s in sp).strip(): continue
            y0 = l['bbox'][1]
            if y0 < 45 or y0 > 565: continue      # 머리글·쪽 번호
            ne = [s for s in sp if s['text'].strip()]
            main = max(s['size'] for s in ne)
            t = ''
            for s in sp:
                x = fix(s['text'], s['font'])
                if s['size'] < main * 0.7 and re.fullmatch(r'\s*\d+\s*', x) and s['font'] == 'GaramondPaliRegular':
                    x = '[^@' + x.strip() + ']'       # 주 번호 — 장 번호는 뒤에서
                t += x
            LINES.append({'pn': pn, 'pg': pg, 'bb': list(l['bbox']), 't': t, 'font': ne[0]['font'], 'size': round(ne[0]['size'], 1), 'spans': [(fix(s['text'], s['font']), s['font'], s['size']) for s in sp]})
# 같은 높이의 조각 줄(차례 '1.' + 'The Birth…', 소제목 'I' + 'THE TRUTH…')은 하나로
M = []
for x in sorted(LINES, key=lambda x: (x['pn'], round(x['bb'][1]), x['bb'][0])):
    if M and M[-1]['pn'] == x['pn'] and abs(M[-1]['bb'][1] - x['bb'][1]) < 3 and x['bb'][0] > M[-1]['bb'][2] - 2:
        M[-1]['t'] = M[-1]['t'].rstrip() + ' ' + x['t'].lstrip(); M[-1]['bb'][2] = x['bb'][2]; M[-1]['spans'] += x['spans']
    else: M.append(x)
LINES = M

# ---------- 2. 줄 끝 하이픈 판단용 낱말 수 (줄 가운데에 쓰인 꼴) ----------
W = collections.Counter()
for x in LINES:
    for w in re.findall(r"[A-Za-zĀāĪīŪūṃṅñṭḍṇḷṄÑṬḌṆḶ’'-]+", x['t'])[:-1]: W[w.lower().strip("’'")] += 1
PREF = ('self', 'non', 'well', 'ill', 'co', 'semi', 'half', 'all', 'ever', 'over', 'under', 'fore', 'pre', 'post', 'anti', 'quasi', 'pseudo', 'ex', 'counter')
HY = []


def join(a, b, pg):
    if not a: return b
    if a.endswith('\xad'): return a[:-1] + b
    m = re.search(r"([A-Za-zĀāĪīŪūṃṅñṭḍṇḷ’']+)-$", a)
    if m and re.match(r'[a-zāīūṃṅñṭḍṇḷ]', b):
        w2 = re.match(r"[A-Za-zĀāĪīŪūṃṅñṭḍṇḷ’']+", b).group(0)
        whole, hyph = (m.group(1) + w2).lower(), (m.group(1) + '-' + w2).lower()
        zw, z1, z2 = zipf(whole, 'en'), zipf(m.group(1).lower(), 'en'), zipf(w2.lower(), 'en')
        if W[hyph] > W[whole] or (W[hyph] == W[whole] == 0 and zw < 1.5 and (m.group(1).lower() in PREF or (z1 >= 3 and z2 >= 3))):
            HY.append((pg, m.group(1) + '-' + w2, '하이픈 남김', W[hyph], W[whole])); return a + b
        HY.append((pg, m.group(1) + w2, '붙임', W[hyph], W[whole])); return a[:-1] + b
    if a.endswith('-') or a.endswith('—'): return a + b
    return a + ' ' + b


def speaker(t, spans):
    """줄 첫머리 굵은 작은 대문자(말하는 이) → **…**"""
    n = 0; s0 = ''
    for txt, f, sz in spans:
        if 'Bold' in f and 'Garamond' in f: s0 += txt; n += 1
        else: break
    s0 = s0.strip()
    if n and t.startswith(s0) and len(s0) > 3:
        m = re.match(r'(.*?)(\.?)$', s0)
        rest = t[len(s0):]
        if rest.startswith('.'): s0, rest = s0 + '.', rest[1:]
        return '**' + s0 + '**' + rest
    return t


# ---------- 3. 문단 ----------
paras = []; cur = None; chap = 0; prev = None; notechap = 0
for x in LINES:
    pn, pg, bb, f, sz = x['pn'], x['pg'], x['bb'], x['font'], x['size']
    t = re.sub(r'[ \t ]+', ' ', x['t']).strip()
    newpage = prev is None or prev['pn'] != pn
    gap = bb[1] - prev['bb'][1] if prev is not None and not newpage else 99
    if pn in NOTES:
        if f.startswith('HumanistPali-Bold'): cur = None; prev = x; continue          # NOTES
        m = re.fullmatch(r'CHAPTER (\d+)', t)
        if m: notechap = int(m.group(1)); cur = None; prev = x; continue
        m = re.match(r'(\d+)\.\s+(.*)', t)
        if m and bb[0] > 62:
            cur = {'pg': pg, 'k': 'fn', 't': f'[^{notechap}.{m.group(1)}]: {m.group(2)}'}; paras.append(cur)
        else: cur['t'] = join(cur['t'], t, pg)
        prev = x; continue
    t = t.replace('[^@', '[^@')
    if f.startswith('HumanistPali-Bold') and sz >= 13.5:       # 장·앞쪽 제목
        if re.fullmatch(r'\d+', t) and pn >= 19: chap = int(t)
        if cur and cur['k'] == 'h' and cur.get('big') and prev is not None and not newpage and gap < 40:
            cur['t'] += ' ' + t
        else:
            cur = {'pg': pg, 'k': 'h', 't': t, 'big': 1}; paras.append(cur)
        prev = x; continue
    t = t.replace('[^@', f'[^{chap}.')
    if pn == 7:                                                   # 차례
        cur = {'pg': pg, 'k': 'toc', 't': t} if not re.fullmatch(r'\d+\.', t) else {'pg': pg, 'k': 'toc', 't': t, 'num': 1}
        if paras and paras[-1].get('num'): paras[-1]['t'] += ' ' + t; paras[-1].pop('num')
        else: paras.append(cur)
        prev = x; continue
    kind = 'pq' if pn == 8 else 'p'
    if f.startswith('HumanistPali-Bold') or (pn in (3, 4) and f.startswith('HumanistPali')):   # 소제목·반표제·속표지 줄
        cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur); prev = x; continue
    if pn == 4 or pn == 5:                                        # 속표지·판권 면: 인쇄된 줄(빈 줄로 나뉜 묶음)마다
        if pn == 5 and (f.startswith('Humanist') or 'pariyatti.org' in t or 'Gore Road' in t or 'Onalaska' in t): kind = 'pq'
        if cur is None or cur['k'] != kind or newpage or gap > 14 or kind == 'p' and pn == 4:
            cur = {'pg': pg, 'k': kind, 't': t}; paras.append(cur)
        else: cur['t'] = join(cur['t'], t, pg)
        prev = x; continue
    x0, x1 = bb[0], bb[2]
    t = speaker(t, x['spans'])
    if x0 >= 140 or (len(t) < 50 and re.match(r'(cf\. )?(Vin|D|M|S|A|Sn|Ud|Dh|Thag|Thig|Iti|Khp|J|Comy)\. \S', t)):   # 출처·서명 줄 (오른쪽, 6쪽 'D. 14' 는 가운데)
        if cur is not None and cur.get('src') and not newpage and gap < 14: cur['t'] += ' ' + t
        else: cur = {'pg': pg, 'k': kind, 't': t, 'src': 1}; paras.append(cur)
    elif x0 >= 80:                                                # 게송
        if cur is not None and cur.get('v') and (newpage or gap <= 16): cur['t'] += '\n' + t
        else: cur = {'pg': pg, 'k': kind, 't': t, 'v': 1}; paras.append(cur)
    else:                                                         # 산문
        if pn == 393 and (t.startswith('Event') or (cur is not None and cur.get('tab') and not t.startswith('*'))):   # 연표 — 줄마다
            if t.startswith('Event'): cur = {'pg': pg, 'k': kind, 't': t, 'tab': 1}; paras.append(cur)
            else: cur['t'] += '\n' + t
            prev = x; continue
        cont = cur is not None and cur['k'] == kind and not cur.get('v') and not cur.get('src') and cur['k'] != 'h' and x0 < 60 and (newpage or gap < 16)
        if cont: cur['t'] = join(cur['t'], t, pg)
        else: cur = {'pg': pg, 'k': kind, 't': t}; paras.append(cur)
    prev = x

for p in paras:
    if p['k'] == 'p' and re.fullmatch(r'\([^()]{3,70}\)', p['t']): p['k'] = 'h'          # 경 이름 소제목 '(The Fire Sermon)'
    if p['pg'] == '205' and p['k'] == 'p' or p['t'] == 'CONTENTS': p['k'] = 'toc'         # 12장 앞 차례 쪽(205)·차례 제목
    for k in ('big', 'v', 'src', 'num', 'tab'): p.pop(k, None)
    p['t'] = re.sub(r' {2,}', ' ', p['t']).strip()
    if p['pg'] and re.fullmatch(r'\d+', p['pg']): p['pdf'] = str(int(p['pg']) + 18)
out = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(out, exist_ok=True)
json.dump(paras, open(os.path.join(out, 'DL-0030.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
with open(os.path.join(out, 'DL-0030.en.hyph.tsv'), 'w') as f:
    f.write('쪽\t낱말\t판단\t하이픈 꼴 수\t붙인 꼴 수\n')
    for r in HY: f.write('\t'.join(map(str, r)) + '\n')
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)), '하이픈', collections.Counter(r[2] for r in HY))
