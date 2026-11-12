"""『법구경 이야기 1』(DL-0023) 31쪽 사끼야 족·꼴리야 족 가계도를 깨끗한 그림으로 다시 그림.
  python3 tools/dl0023_family.py
글자·짜임은 한글 파일 속 도표(메타파일)의 글자와 선 그대로 — 이름 표기도 책 그대로(도표의 오자 '마미또다나'만 '아미또다나'로 고침).
SVG 를 만들고 rsvg-convert 로 2배 PNG (public/uploads/DL-0023-sakya.png, DL-0023-koliya.png).
"""
import os, subprocess
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FS = 21          # 글자 크기
LV = 112         # 단계 사이 높이
FONT = "Noto Sans CJK KR, Noto Sans KR, sans-serif"

def tw(s, fs=FS):
    return sum(fs * (1.0 if ord(c) > 0x2000 else 0.56) for c in s)

def draw(name, title, nodes, W):
    """nodes: (id, 부모 id, 단계, x, 이름, 둘째 줄)"""
    pos, out = {}, []
    H = max(n[2] for n in nodes) * LV + 125
    for nid, par, lv, x, lab, sub in nodes:
        y = 40 + lv * LV
        w = max(tw(lab), tw(sub, FS - 3) if sub else 0) + 26
        h = 40 if not sub else 64
        pos[nid] = (x, y, w, h)
    # 선: 부모 → 아이들
    kids = {}
    for n in nodes:
        if n[1]: kids.setdefault(n[1], []).append(n[0])
    for p, ks in kids.items():
        px, py, pw, ph = pos[p]
        top = min(pos[k][1] for k in ks)
        mid = top - 26
        out.append(f'<line x1="{px}" y1="{py+ph}" x2="{px}" y2="{mid}"/>')
        xs = [pos[k][0] for k in ks] + [px]
        if len(xs) > 1 and min(xs) != max(xs):
            out.append(f'<line x1="{min(xs)}" y1="{mid}" x2="{max(xs)}" y2="{mid}"/>')
        for k in ks:
            kx, ky, _, _ = pos[k]
            out.append(f'<line x1="{kx}" y1="{mid}" x2="{kx}" y2="{ky}"/>')
    lines = '\n'.join(out)
    boxes = []
    for nid, par, lv, x, lab, sub in nodes:
        x0, y, w, h = pos[nid]
        root = par is None
        fill = '#e9e2d3' if root else '#fbf9f4'
        boxes.append(f'<rect x="{x0-w/2:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="9" fill="{fill}" stroke="#a89a7c" stroke-width="1.6"/>')
        fw = ' font-weight="700"' if root else ''
        boxes.append(f'<text x="{x0}" y="{y+27}" font-size="{FS+ (2 if root else 0)}"{fw}>{lab}</text>')
        if sub: boxes.append(f'<text x="{x0}" y="{y+52}" font-size="{FS-3}" fill="#6b5f48">{sub}</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" fill="#ffffff"/>
<g stroke="#5c5444" stroke-width="2.2" fill="none" stroke-linecap="square">
{lines}
</g>
<g font-family="{FONT}" text-anchor="middle" fill="#2a261e">
{chr(10).join(boxes)}
</g>
</svg>'''
    d = '/tmp/dl0023'; os.makedirs(d, exist_ok=True)
    sp = os.path.join(d, name + '.svg'); open(sp, 'w').write(svg)
    png = os.path.join(REPO, 'public/uploads', f'DL-0023-{name}.png')
    subprocess.run(['rsvg-convert', '-z', '2', '-o', png, sp], check=True)
    print(png)

# 사끼야 족 (한글 파일 31쪽 첫 도표)
draw('sakya', '사끼야 족', [
    ('r', None, 0, 640, '사끼야 족', ''),
    ('a', 'r', 1, 470, '시하하누+깟짜나', ''),
    ('b', 'r', 1, 1010, '야소다라', ''),
    ('c1', 'a', 2, 205, '숫도다나(왕)', ''),
    ('c2', 'a', 2, 352, '돗또다나', ''),
    ('c3', 'a', 2, 482, '삭꼬다나', ''),
    ('c4', 'a', 2, 650, '숫꼬다나', ''),
    ('c5', 'a', 2, 825, '아미또다나', ''),   # 한글 파일 도표에는 '마미또다나' — 오자, 운영자 요청으로 고침 (2026-11-12)
    ('c6', 'a', 2, 950, '아미따', ''),
    ('c7', 'a', 2, 1060, '빠미따', ''),
    ('d1', 'c1', 3, 100, '+ 마하마야', ''),
    ('d2', 'c1', 3, 315, '+ 마하빠자빠띠고따미', ''),
    ('e1', 'c4', 3, 585, '마하나마', '(왕)'),
    ('e2', 'c4', 3, 715, '아누룻다', '(장로)'),
    ('f1', 'c5', 3, 825, '아난다', '(장로)'),
    ('g1', 'c6', 3, 950, '띳사', '(장로)'),
    ('h1', 'd1', 4, 100, '싯닷따+야소다라', '(붓다)'),
    ('i1', 'h1', 5, 100, '라훌라', '(장로)'),
], 1130)

# 꼴리야 족 (둘째 도표)
draw('koliya', '꼴리야 족', [
    ('r', None, 0, 560, '꼴리야 족', ''),
    ('a', 'r', 1, 330, '안자나+야소다라', ''),
    ('b', 'r', 1, 820, '깟짜나', ''),
    ('c1', 'a', 2, 140, '숩빠붓다+빠미따', ''),
    ('c2', 'a', 2, 330, '단다빠니', ''),
    ('c3', 'a', 2, 480, '마하마야', ''),
    ('c4', 'a', 2, 690, '마하빠자빠띠 고따미', '(장로니)'),
    ('d1', 'c1', 3, 75, '데와닷따', '(장로)'),
    ('d2', 'c1', 3, 205, '야소다라', '(장로니)'),
], 900)
