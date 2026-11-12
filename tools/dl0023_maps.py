"""『법구경 이야기 1』(DL-0023) 앞의 지도 두 장 — '부처님 당시 인도 B.C 500년경'·'불교중심지역 majjhimadesa' — 을 새로 그림.
  python3 tools/dl0023_maps.py 인쇄본.pdf
인쇄본 PDF(스캔) 2·3쪽의 지도에서 해안선·강 선만 뽑아 깨끗하게 다듬고, 글자는 모두 글꼴로 다시 씀(글자·자리는 인쇄본 그대로).
둘째 지도는 인쇄본에서 옆으로 눕혀 실렸으므로 바로 세움(북쪽이 위). 결과: public/uploads/DL-0023-map-india.png, DL-0023-map-majjhimadesa.png
한글 파일에는 이 지도가 없음(본문 글은 한글 파일 그대로, 이 도구는 그림만 만듦).
"""
import sys, os, io, base64, subprocess
import numpy as np, cv2, fitz
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = '/tmp/dl0023/maps'; os.makedirs(WORK, exist_ok=True)
doc = fitz.open(sys.argv[1])

def scan(pno, rotate=False):
    x = doc[pno].get_images()[0][0]
    g = np.array(Image.open(io.BytesIO(doc.extract_image(x)['image'])).convert('L'))
    if rotate: g = cv2.rotate(g, cv2.ROTATE_90_CLOCKWISE)
    return g

def line_layer(g, blank=()):
    """회색 선만 남김: 검은 글자·점은 빼고, 글자 때문에 끊긴 곳은 이어 붙임"""
    black = (g < 80).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(black, 8)
    txt = np.zeros_like(black)
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if max(w, h) < 120 and a >= 25 and max(w, h) >= 8: txt[lab == k] = 1
    txt = cv2.dilate(txt, np.ones((11, 11), np.uint8))
    ink = (g < 238).astype(np.uint8) & (1 - txt)
    for (x0, y0, x1, y1) in blank: ink[y0:y1, x0:x1] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
    keep = np.zeros_like(ink)
    for k in range(1, n):
        if st[k, cv2.CC_STAT_AREA] >= 45: keep[lab == k] = 1
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    # 가운데 줄만 남겨(뼈대) 같은 굵기로 다시 그림
    sk = cv2.ximgproc.thinning(keep * 255) if hasattr(cv2, 'ximgproc') else None
    if sk is None:
        from skimage.morphology import skeletonize
        sk = skeletonize(keep > 0).astype(np.uint8) * 255
    n, lab, st, _ = cv2.connectedComponentsWithStats((sk > 0).astype(np.uint8), 8)
    clean = np.zeros_like(sk)
    for k in range(1, n):
        if st[k, cv2.CC_STAT_AREA] >= 25: clean[lab == k] = 255
    thick = cv2.dilate(clean, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    thick = cv2.GaussianBlur(thick, (0, 0), 1.0)
    rgba = np.zeros(g.shape + (4,), np.uint8); rgba[..., :3] = (120, 128, 138); rgba[..., 3] = thick
    buf = io.BytesIO(); Image.fromarray(rgba).save(buf, 'PNG')
    return base64.b64encode(buf.getvalue()).decode()

FONT = "Noto Sans CJK KR, Noto Sans KR, sans-serif"
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;')
def T(x, y, s, size, weight=400, anchor='middle', rot=0, fill='#1f1d1a', halo=True, italic=False):
    tr = f' transform="rotate({rot} {x} {y})"' if rot else ''
    st = ' font-style="italic"' if italic else ''
    h = f' stroke="#fff" stroke-width="{max(4, size // 6)}" stroke-linejoin="round" paint-order="stroke"' if halo else ''
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" dominant-baseline="central" fill="{fill}"{st}{h}{tr}>{esc(s)}</text>'
def DOT(x, y, r=11): return f'<circle cx="{x}" cy="{y}" r="{r}" fill="#1f1d1a" stroke="#fff" stroke-width="3"/>'
def TRI(x, y, s=13): return f'<path d="M{x} {y - s} L{x + s} {y + s * .8} L{x - s} {y + s * .8} Z" fill="#1f1d1a"/>'
def REGION(x, y, s, size=46): return T(x, y, s, size, 700)
def CITY(dx, dy, s, tx, ty, anchor='start', r=11, size=34): return DOT(dx, dy, r) + T(tx, ty, s, size, 400, anchor)

def render(name, W, H, img, parts, iw=None):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" fill="#fff"/>
<image x="0" y="0" width="{iw or W}" height="{H}" xlink:href="data:image/png;base64,{img}"/>
<g font-family="{FONT}">
{chr(10).join(parts)}
</g></svg>'''
    sp = os.path.join(WORK, name + '.svg'); open(sp, 'w').write(svg)
    out = os.path.join(REPO, 'public/uploads', f'DL-0023-{name}.png')
    subprocess.run(['rsvg-convert', '-o', out, sp], check=True)
    # 받는 크기를 줄이려고 색 수를 줄여 저장
    im = Image.open(out).convert('RGB'); im.quantize(colors=64, method=Image.Quantize.MEDIANCUT).save(out, optimize=True)
    print(out, im.size, os.path.getsize(out) // 1024, 'KB')

# ---- 1. 부처님 당시 인도 B.C 500년경 (인쇄본 2쪽) ----
g = scan(1)
H1, W1 = g.shape
img = line_layer(g, blank=[(0, 0, W1, 260)])
P = [
    T(50, 158, '부처님 당시 인도', 92, 700, 'start', halo=False),
    T(712, 166, 'B.C 500년경', 60, 400, 'start', halo=False),
    f'<rect x="1080" y="112" width="11" height="88" fill="#1f1d1a"/>',
    REGION(650, 355, '깜보자'), REGION(670, 560, '간다라'),
    CITY(610, 607, '딱까실라', 590, 605, 'end'),
    TRI(1152, 745) + T(1180, 745, '시네루 산', 38, 400, 'start'),
    DOT(1153, 787) + T(1182, 787, '아노땃따 호수', 38, 400, 'start'),
    REGION(903, 838, '꾸루'), REGION(1020, 922, '빤짤라'), REGION(1295, 925, '사끼야'),
    CITY(1219, 991, '까삘라왓투', 1237, 968, r=15),
    REGION(1088, 990, '꼬살라'),
    DOT(1162, 997) + T(1170, 1036, '사왓티', 34),
    REGION(1308, 1048, '말라'), REGION(1422, 1032, '왓지'),
    REGION(688, 1020, '맛차'), REGION(875, 1088, '수라세나'),
    CITY(1372, 1096, '웨살리', 1388, 1090),
    CITY(1346, 1123, '빠딸리가마', 1360, 1130),
    CITY(1125, 1130, '꼬삼비', 1108, 1133, 'end'),
    DOT(1197, 1148, 15) + T(1196, 1112, '베나레스', 34),
    REGION(1578, 1152, '앙가'),
    CITY(1341, 1170, '라자가하', 1360, 1173),
    REGION(1033, 1192, '왐사'), REGION(1205, 1198, '까시'),
    CITY(1316, 1211, '보드가야', 1332, 1212),
    CITY(791, 1258, '웃제니', 806, 1257),
    REGION(960, 1250, '쩨디'), REGION(793, 1310, '아완띠'), REGION(1327, 1298, '마가다'),
    REGION(755, 1455, '앗사까'),
    CITY(621, 1528, '숩빠라까', 636, 1525),
    REGION(1202, 1598, '깔링가'), REGION(958, 1697, '안드라'), REGION(1083, 2325, '싱할라'),
    f'<rect x="245" y="1390" width="88" height="4" fill="#1f1d1a"/>',
    T(289, 1440, '16대국', 40, 400),
    f'<rect x="245" y="1488" width="88" height="4" fill="#1f1d1a"/>',
]
for k, s in enumerate('마가다 꼬살라 앙가 까시 왓지 말라 쩨디 왐사 꾸루 빤짤라 맛차 수라세나 앗사까 아완띠 간다라 깜보자'.split()):
    P.append(T(289, 1537 + 48 * k, s, 38, 400, halo=False))
P.append(f'<rect x="245" y="2303" width="88" height="4" fill="#1f1d1a"/>')
render('map-india', W1, H1, img, P)

# ---- 2. 불교중심지역 majjhimadesa (인쇄본 3쪽, 옆으로 실린 것을 바로 세움) ----
g = scan(2, rotate=True)
H2, W2 = g.shape
img = line_layer(g, blank=[(2280, 0, W2, H2)])   # 오른쪽의 세로 제목 자리
R = lambda x, y, s: REGION(x, y, s, 50)
C = lambda dx, dy, s, tx, ty, a='start', r=12: CITY(dx, dy, s, tx, ty, a, r, 38)
RIV = lambda x, y, s, rot: T(x, y, s, 32, 400, 'middle', rot, fill='#4f5965', italic=False)
P = [
    T(120, 150, '불교중심지역', 96, 700, 'start', halo=False),
    T(690, 162, 'majjhimadesa', 62, 400, 'start', halo=False),
    f'<rect x="1130" y="104" width="11" height="96" fill="#1f1d1a"/>',
    R(247, 622, '빤짤라'), R(729, 632, '꼬살라'), R(1103, 482, '사끼야'), R(953, 1158, '까시'),
    R(639, 1302, '왐사'), R(1425, 410, '꼴리야'), R(1320, 912, '말라'), R(1600, 955, '왓지'),
    R(2048, 1010, '앙가'), R(1912, 1362, '마가다'),
    DOT(806, 684, 17) + T(802, 728, '사왓티(사위성)', 38),
    DOT(1105, 677, 17) + T(1042, 635, '까삘라왓투', 38),
    C(1157, 615, '룸비니', 1177, 613),
    DOT(1176, 836) + T(1152, 800, '꾸시나라', 38),
    C(1242, 835, '빠와', 1262, 833),
    T(272, 833, '상깟사', 38),
    DOT(945, 852) + T(968, 852, '사께따', 38, 400, 'start'),
    DOT(1133, 1257) + T(1150, 1290, '이시빠따나 (녹야원)', 38, 400, 'start'),
    DOT(1094, 1302, 17) + T(1085, 1345, '베나레스(바라나시)', 38, 400, 'start'),
    DOT(773, 1298, 17) + T(741, 1255, '꼬삼비', 38),
    C(1648, 1053, '웨살리(바이샬리)', 1673, 1053, r=17),
    C(1578, 880, '알라위', 1600, 878),
    DOT(1616, 1138) + T(1556, 1180, '빠딸리가마', 38),
    C(1677, 1193, '날라까', 1698, 1192),
    C(1703, 1263, '라자가하(왕사성)', 1727, 1262, r=17),
    C(1645, 1318, '가야', 1662, 1318),
    C(1648, 1360, '보드가야', 1668, 1362),
    C(1605, 1397, '우루웰라', 1585, 1398, 'end'),
    C(2058, 1189, '짬빠', 2077, 1190),
    RIV(932, 694, '아찌라와디 강', 24), RIV(765, 876, '사라부 강', 22), RIV(520, 1162, '야무나 강', 10),
    RIV(1325, 1142, '강가 강(겐지스)', -22), RIV(1405, 815, '마히 강', 52),
]
render('map-majjhimadesa', 2290, H2, img, P, iw=W2)
