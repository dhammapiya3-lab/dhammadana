#!/usr/bin/env python3
"""빠알리어 한글 표기(발음 부호가 붙은 한글)를 PaliHangul 글꼴로 제대로 보이게 (운영자 요청, 2026-11-10)
  python3 tools/pali_hangul.py PaliHangul-Web.otf DL-0018 [DL-…]

책 본문(content/texts/<ID>.json 의 body)의 글자는 바꾸지 않는다. 화면에 보일 때만 바꿀 낱말 사전 `ph` 를 텍스트 JSON 에 넣음:
  인쇄본(한컴 바탕)의 부호 → PaliHangul 글꼴의 부호 (글꼴이 음절+부호를 한 글자 그림으로 합침)
  〬 대기음 → U+030A, 〭 권설음 → U+0325, ᷇ 장모음 → U+FE20, ̫ ñ → U+0330, ͌ la → U+0303,
  ″ 자음 중복 → U+02BA, ᷾ ya → U+0346, ᷃ va → U+030C, ˑ ṅ → U+02D1, ˕ 끝소리에 → U+FE00, ˔ 첫소리에 → U+FE01
  - 같은 부호가 두 번 겹친 것(PDF 겹쳐 찍기)은 하나로
  - 부호 순서를 바꿔 보거나, 첫소리에 붙을 수 없는 아랫점(빳〭·앗〭)은 끝소리(U+FE00)로 — 글꼴이 한 글자로 합치는 것을 고름
  - 그래도 합쳐지지 않으면 〬 〭 는 인쇄본처럼 오른쪽 위·아래 작은 고리(글꼴에 있음)로 그대로 둠 → 목록을 알림
  - 텍스트 JSON 의 `ph_fix` {책 본문 낱말: 바른 표기}가 있으면 그 표기로 보임 (운영자 요청: 350쪽 사띠빳〭˕타〭᷇나᷇ = satipaṭṭhānā)
그리고 쓰인 글자만 담은 작은 글꼴 public/fonts/PaliHangul.woff2 를 만든다.
"""
import itertools, json, re, subprocess, sys, tempfile, uharfbuzz as hb
from fontTools.ttLib import TTFont

M = '̫〭᷇͌〬″᷾᷃ˑ˔˕'
MAP = {'〬': '̊', '〭': '̥', '᷇': '︠', '̫': '̰', '͌': '̃', '″': 'ʺ', '᷾': '͆', '᷃': '̌', 'ˑ': 'ˑ', '˔': '︁', '˕': '︀'}
KEEP = {'〬': '\u302C', '〭': '\u302D', '″': '\u2033'}
WRE = re.compile('(?:[가-힣][' + M + ']*)+')
SYL = re.compile('([가-힣])([' + M + ']*)')

font_path, ids = sys.argv[1], sys.argv[2:]
data = open(font_path, 'rb').read()
hbfont = hb.Font(hb.Face(data))
order = TTFont(font_path).getGlyphOrder()
MARKG = set()
cm = TTFont(font_path).getBestCmap()
for u in set(MAP.values()) | set(KEEP.values()): MARKG.add(cm.get(ord(u)))


def composed(s):
    buf = hb.Buffer(); buf.add_str(s); buf.guess_segment_properties(); hb.shape(hbfont, buf, {})
    return not any(order[g.codepoint] in MARKG for g in buf.glyph_infos)


left = []


def syl(base, ms):
    seen = []
    for c in ms:
        if c not in seen: seen.append(c)
    if not seen: return base
    vs = [c for c in seen if c in '˔˕']; core = [c for c in seen if c not in '˔˕']
    tries = []
    for perm in itertools.permutations(core):
        tries.append(base + ''.join(MAP[c] for c in perm) + ''.join(MAP[c] for c in vs))
    if not vs and '〭' in core:
        for perm in itertools.permutations(core):
            tries.append(base + ''.join(MAP[c] for c in perm) + '︀')
    for t in tries:
        if composed(t): return t
    # 합쳐지지 않음: 합쳐지는 부호만 쓰고, 나머지는 인쇄본 모양 그대로
    left.append(base + ''.join(seen))
    best = base
    for c in core:
        t = best + MAP[c]
        best = t if composed(t) else best + KEEP.get(c, MAP[c])
    return best + ''.join(MAP[c] for c in vs)


allw = set()
for bid in ids:
    p = f'content/texts/{bid}.json'
    t = json.load(open(p))
    ws = sorted({w for w in WRE.findall(t['body']) if re.search('[' + M + ']', w)})
    fix = t.get('ph_fix', {})  # 운영자가 정한 바른 표기 {책 본문 낱말: 책과 같은 부호로 쓴 바른 표기} — 본문은 그대로, 화면에만
    t['ph'] = {w: SYL.sub(lambda m: syl(m.group(1), m.group(2)), fix.get(w, w)) for w in ws}
    allw |= set(t['ph'].values())
    open(p, 'w').write(json.dumps(t, ensure_ascii=False, indent=2) + '\n')
    print(f'{bid}: 낱말 {len(ws)}개')
if left: print('글꼴에 합친 글자가 없어 부호를 따로 둔 곳:', ' '.join(sorted(set(left))))
with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
    f.write('\n'.join(sorted(allw)))
subprocess.run(['pyftsubset', font_path, '--text-file=' + f.name, '--unicodes=U+0020,U+FE00,U+FE01,U+302C,U+302D',
                '--layout-features=ccmp,liga,rlig', '--flavor=woff2', '--output-file=public/fonts/PaliHangul.woff2'], check=True)
print('public/fonts/PaliHangul.woff2 만듦')
