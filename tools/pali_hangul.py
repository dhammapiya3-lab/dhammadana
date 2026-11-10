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
SOLO = {c: 0xE900 + i for i, c in enumerate('″̫᷾᷃᷇˔˕')}  # 혼자 쓰인 부호 → 글꼴에 더한 띄어 쓰는 부호 글자(PUA)
KEEP = {'〬': '\u302C', '〭': '\u302D', '″': '\u2033'}
WRE = re.compile('(?:[가-힣][' + M + ']*)+')
SYL = re.compile('([가-힣])([' + M + ']*)')

font_path, ids = sys.argv[1], sys.argv[2:]


def patch_font(src):
    """글꼴에 없는 조합을 글꼴 안의 같은 표시를 옮겨 붙여 새 글자로 더함 (운영자 요청, 2026-11-10):
    뱌᷇ ← 바᷇ 의 장음 줄, 딴̫ ← 빤̫ 의 ñ 물결, 로″ ← 요″ 의 중복 표시. 표시 모양·자리는 글꼴에 원래 있던 그대로."""
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.t2CharStringPen import T2CharStringPen
    from fontTools.ttLib.tables import otTables as ot
    f = TTFont(src); gs = f.getGlyphSet(); cm = f.getBestCmap(); hf = hb.Font(hb.Face(open(src, 'rb').read()))
    order = f.getGlyphOrder()
    G = lambda ch: cm[ord(ch)]
    def lig(s):
        b = hb.Buffer(); b.add_str(s); b.guess_segment_properties(); hb.shape(hf, b, {})
        g = [order[i.codepoint] for i in b.glyph_infos]; assert len(g) == 1, s; return g[0]
    def contours(gn):
        p = RecordingPen(); gs[gn].draw(p); out, cur = [], []
        for op, a in p.value:
            cur.append((op, a))
            if op in ('closePath', 'endPath'): out.append(tuple(cur)); cur = []
        return out
    def marks(ref, base):
        b = set(contours(G(base))); return [c for c in contours(lig(ref)) if c not in b]
    NEW = [('ph.bya_long', '뱌', marks('바\uFE20', '바'), ['uniFE20']),
           ('ph.ttan_ny', '딴', marks('빤\u0330', '빤'), ['uni0330']),
           ('ph.ro_dbl', '로', marks('요\u02BA', '요'), ['uni02BA'])]
    cff = f['CFF '].cff; top = cff.topDictIndex[0]; cs = top.CharStrings
    tgt = None
    for lk in f['GSUB'].table.LookupList.Lookup:
        if lk.LookupType == 4:
            tgt = next((st for st in lk.SubTable if G('다') in st.ligatures), None)
            if tgt: break
    for name, base, mk, comp in NEW:
        assert mk, name
        rp = RecordingPen(); gs[G(base)].draw(rp)
        pen = T2CharStringPen(f['hmtx'][G(base)][0], gs); rp.replay(pen)
        for c in mk:
            for op, a in c: getattr(pen, op)(*a)
        cs.charStrings[name] = len(cs.charStringsIndex); cs.charStringsIndex.append(pen.getCharString(private=top.Private, globalSubrs=cff.GlobalSubrs))
        top.charset.append(name); order.append(name); f['hmtx'][name] = f['hmtx'][G(base)]
        lg = ot.Ligature(); lg.LigGlyph = name; lg.Component = comp; lg.CompCount = 1 + len(comp)
        tgt.ligatures.setdefault(G(base), []).insert(0, lg)
    # 글자 없이 혼자 쓰인 부호(437·439쪽 표기 설명)를 보여 줄 '띄어 쓰는' 부호 글자 — 글꼴의 부호 모양 그대로, 옆 글자와 겹치지 않게
    def rect(x0, y0, x1, y1): return (('moveTo', ((x0, y0),)), ('lineTo', ((x1, y0),)), ('lineTo', ((x1, y1),)), ('lineTo', ((x0, y1),)), ('closePath', ()))
    SOLO_SHAPES = {'″': marks('야\u02BA', '야'), '᷾': marks('이\u0346', '이'), '᷃': marks('오\u030C', '오'),
                   '᷇': marks('바\uFE20', '바'), '̫': marks('냐\u0330', '냐'),
                   '˔': [rect(40, 300, 280, 340), rect(140, 340, 180, 560)],   # ⊥ 위쪽 점 → 첫소리 (인쇄본 모양)
                   '˕': [rect(40, 520, 280, 560), rect(140, 300, 180, 520)]}   # ⊤ 아래쪽 점 → 끝소리
    cmap_tables = [t for t in f['cmap'].tables if t.isUnicode()]
    for ch, mk in SOLO_SHAPES.items():
        assert mk, ch
        xs = [x for c in mk for op, a in c for x, y in a]; dx = 60 - min(xs); w = max(xs) - min(xs) + 120
        pen = T2CharStringPen(w, gs)
        for c in mk:
            for op, a in c: getattr(pen, op)(*[(x + dx, y) for x, y in a])
        name = 'ph.solo%04X' % ord(ch)
        cs.charStrings[name] = len(cs.charStringsIndex); cs.charStringsIndex.append(pen.getCharString(private=top.Private, globalSubrs=cff.GlobalSubrs))
        top.charset.append(name); order.append(name); f['hmtx'][name] = (w, 60)
        for t in cmap_tables: t.cmap[SOLO[ch]] = name
    f.setGlyphOrder(order); f['maxp'].numGlyphs = len(order)
    out = tempfile.mktemp(suffix='.otf'); f.save(out); return out


font_path = patch_font(font_path)
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
    for m in re.finditer('(?<![가-힣' + M + '])([' + M + '])', t['body']):
        c = m.group(1)
        if ord(c) in (0x2033,) or c in SOLO: t['ph'][c] = chr(SOLO[c])
    allw |= set(t['ph'].values())
    open(p, 'w').write(json.dumps(t, ensure_ascii=False, indent=2) + '\n')
    print(f'{bid}: 낱말 {len(ws)}개')
if left: print('글꼴에 합친 글자가 없어 부호를 따로 둔 곳:', ' '.join(sorted(set(left))))
with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
    f.write('\n'.join(sorted(allw)))
subprocess.run(['pyftsubset', font_path, '--text-file=' + f.name, '--unicodes=U+0020,U+FE00,U+FE01,U+302C,U+302D,U+E900-E906',
                '--layout-features=ccmp,liga,rlig', '--flavor=woff2', '--output-file=public/fonts/PaliHangul.woff2'], check=True)
print('public/fonts/PaliHangul.woff2 만듦')
