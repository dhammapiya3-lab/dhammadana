"""『업과 윤회의 법칙』(DL-0034) PDF 읽기 도우미 — 글자 자리로 줄을 다시 세우고, 표·그림 자리를 찾음 (pdf2text_dl0034.py 가 씀)"""
import re, collections
import fitz

MARK = re.compile(r'^\s*(?:\*\*)?\s*(?:-\s|[①-⑳㉑-㉟]|\d+\)|\d+\.|\d+[-~]\d+\)|\[\d+(?:-\d+)?\])')


def runion(a, b):
    return fitz.Rect(min(a.x0, b.x0), min(a.y0, b.y0), max(a.x1, b.x1), max(a.y1, b.y1))


def merge_rects(rs, pad):
    rs = [fitz.Rect(r) for r in rs]; merged = True
    while merged:
        merged = False; out = []
        for r in rs:
            for k, o in enumerate(out):
                if (o + (-pad, -pad, pad, pad)).intersects(r):
                    out[k] = runion(o, r); merged = True; break
            else: out.append(r)
        rs = out
    return rs


class Page:
    def __init__(self, doc, n):
        self.n = n; p = self.p = doc[n - 1]
        self.L = 70.9 if n % 2 or n < 35 else 56.7
        self.R = self.L + 297.5
        self.boldkeys = set()
        try:
            for s in p.get_texttrace():
                if s['type'] == 1:
                    for ch in s['chars']:
                        self.boldkeys.add((round(ch[2][0]), round(ch[2][1])))
        except Exception:
            pass
        self.chars = []; seen = set(); self.rot = []
        for b in p.get_text('rawdict')['blocks']:
            if b.get('type') == 1: continue
            for l in b.get('lines', []):
                rot = abs(l['dir'][0] - 1) > 0.01
                for s in l['spans']:
                    for c in s['chars']:
                        if rot:
                            self.rot.append(fitz.Rect(c['bbox'])); continue
                        x, y = c['origin']
                        k = (c['c'], round(x * 2), round(y * 2))
                        if k in seen: continue
                        seen.add(k)
                        self.chars.append(dict(c=c['c'], x=x, y=y, x1=c['bbox'][2], y0=c['bbox'][1], size=s['size'], font=s['font'],
                                               bold=('Bold' in s['font']) or (round(x), round(y)) in self.boldkeys,
                                               ital='Italic' in s['font'], flags=s['flags']))
        # 그림 선 나누기
        self.fills, self.hl, self.vl, self.boxes = [], [], [], []
        sepc = []
        for g in p.get_drawings():
            r = fitz.Rect(g['rect'])
            if r.y1 < 84 or r.y0 > 590: continue
            if r.height < 1.6 and r.width > 6:
                self.hl.append(r)
                if 125 < r.width < 155 and r.x0 < self.L + 3 and r.y0 > 120 and len(g['items']) == 1: sepc.append(r)
            elif r.width < 1.6 and r.height > 6: self.vl.append(r)
            elif r.width > 3 and r.height > 3:
                (self.fills if g.get('fill') is not None and min(g['fill']) < 0.97 else self.boxes).append(r)
        self.imgs = [fitz.Rect(im['bbox']) for im in p.get_image_info()]
        if self.rot:
            self.imgs.append(fitz.Rect(min(r.x0 for r in self.rot), min(r.y0 for r in self.rot), max(r.x1 for r in self.rot), max(r.y1 for r in self.rot)))
        # 각주 구분선: 다른 선과 붙어 있지 않은 짧은 가로선
        self.fy = None
        for sr in sepc:
            others = [r for r in self.hl + self.vl + self.fills + self.boxes if r is not sr and (r + (-6, -25, 6, 25)).intersects(sr)]
            if not others:
                self.fy = sr.y0; self.hl = [r for r in self.hl if r is not sr]; break

    def _group(self, chars):
        cs = sorted(chars, key=lambda c: (c['y'], c['x'])); cl = []
        for c in cs:
            if cl and abs(cl[-1]['y'] - c['y']) < 1.6: cl[-1]['cs'].append(c)
            else: cl.append(dict(y=c['y'], cs=[c]))
        for g in cl:
            g['cs'].sort(key=lambda c: c['x'])
            sz = [round(c['size'], 1) for c in g['cs'] if c['c'].strip()]
            g['size'] = collections.Counter(sz).most_common(1)[0][0] if sz else 0
        return cl

    def lines(self):
        """[{y,x0,x1,size,cs,zone,text,gaps}] zone: head / foot / fn / body"""
        cl = [g for g in self._group(self.chars) if g['size']]
        out = []
        for g in cl:
            vis = [c for c in g['cs'] if c['c'].strip()]
            txt = ''.join(c['c'] for c in vis)
            # 작은 글씨 조각(위첨자 각주 번호 '3)', '다.36)' 처럼) → 가까운 줄에 붙임
            if g['size'] < 8.6 and len(vis) <= 9 and re.search(r'\d\)', txt):
                tgt = None; best = 99
                for h in cl:
                    if h is g or h['size'] < g['size'] * 1.1: continue
                    d = h['y'] - g['y']
                    if -4 < d < 10 and h['cs'][0]['x'] - 3 < vis[0]['x'] < h['cs'][-1]['x1'] + 10 and abs(d - 3) < best:
                        best = abs(d - 3); tgt = h
                if tgt is not None and (self.fy is None or (g['y'] < self.fy) == (tgt['y'] < self.fy)):
                    for c in g['cs']:
                        if re.match(r'[\d)]', c['c']): c['sup'] = True
                    tgt['cs'] = sorted(tgt['cs'] + g['cs'], key=lambda c: c['x']); continue
            out.append(g)
        # 각주 구분선 확인: 바로 아래 첫 줄이 작은 글씨 'N)' 로 시작해야 함 (표 안의 짧은 가로선과 헷갈리지 않게)
        if self.fy:
            below = sorted([g for g in out if g['y'] > self.fy], key=lambda g: g['y'])
            if below:
                ft = ''.join(c['c'] for c in below[0]['cs']).strip()
                if not (below[0]['size'] < 9.6 and re.match(r'\d+\)', ft)) and not (below[0]['size'] < 9.6 and len(below) and below[0]['y'] - self.fy < 20):
                    self.fy = None
        res = []
        for g in out:
            # 글자와 글자가 붙어 있는데 그 사이에 끼어 있는 빈칸(겹쳐 찍힌 조각) 빼기
            cs = g['cs']; keep = []
            for i, c in enumerate(cs):
                if c['c'] == ' ' and 0 < i < len(cs) - 1:
                    a = next((x for x in reversed(cs[:i]) if x['c'].strip()), None); b = next((x for x in cs[i + 1:] if x['c'].strip()), None)
                    if a and b and b['x'] - a['x1'] < 0.8: continue
                keep.append(c)
            g['cs'] = keep
            for c in g['cs']:
                if not c.get('sup') and c['size'] < g['size'] * 0.82 and re.match(r'[\d)]', c['c']):
                    c['sup'] = True
            vis = [c for c in g['cs'] if c['c'].strip()]
            if not vis: continue
            z = 'body'
            if g['y'] < 84: z = 'head'
            elif g['y'] > 588: z = 'foot'
            elif self.fy and g['y'] > self.fy: z = 'fn'
            gaps = [(b['x'] - a['x1'], a['x1'], b['x']) for a, b in zip(vis, vis[1:])]
            res.append(dict(y=g['y'], x0=vis[0]['x'], x1=max(c['x1'] for c in vis), size=g['size'], cs=g['cs'], zone=z,
                            text=''.join(c['c'] for c in g['cs']), gaps=gaps))
        return res

    def tables(self, L):
        """표·그림 자리 → (img: [rect], cols: [(rect, lines)]) — img 는 그림으로, cols 는 단을 나눈 목록(글로)"""
        body = [l for l in L if l['zone'] == 'body']
        thr = lambda l: max(18, 2.2 * l['size'])
        for l in body:
            vis = [c for c in l['cs'] if c['c'].strip()]
            l['tab'] = False
            for k, (g, a, b) in enumerate(l['gaps']):
                if g <= thr(l): continue
                left = ''.join(c['c'] for c in vis[:k + 1]); right = ''.join(c['c'] for c in vis[k + 1:])
                if MARK.match(left) and len(MARK.match(left).group(0).strip()) >= len(left.strip()) - 0: continue   # '②     단지…' 번호 뒤 빈칸
                if len(right.strip(' .,')) < 2 or len(left.strip()) < 1: continue
                l['tab'] = True; break
            if not l['tab'] and len(self.mcells(l)) >= 2: l['tab'] = True
        drawn = merge_rects(self.fills + self.boxes + self.hl + self.vl, 6)
        img = []; rules = []; self.textboxes = []
        for r in drawn:
            nf = sum(1 for x in self.fills + self.boxes if r.contains(x))
            nh = sum(1 for x in self.hl if r.contains(x)); nv = sum(1 for x in self.vl if r.contains(x))
            fl = [x for x in self.fills + self.boxes if r.contains(x)]
            if fl and not nh and not nv and len(fl) <= 3 and all(x.height < 15 for x in fl):
                continue   # 글 뒤에 깔린 회색 띠(강조) — 표가 아님
            if nf or (nh >= 2 and nv >= 1) or nh >= 3 or (nh >= 1 and nv >= 2):
                # 글이 든 네모 상자(칠한 칸 없음, 안의 줄이 대부분 글 줄) → 글로
                nfill = sum(1 for x in self.fills if r.contains(x))
                inside = [l for l in body if r.contains(fitz.Point(l['x0'] + 1, l['y'] - 1))]
                if not nfill and len(inside) >= 6 and sum(1 for l in inside if not l['tab'] and l['x1'] - l['x0'] > (r.width * 0.75)) >= len(inside) * 0.6:
                    self.textboxes.append(r); continue
                img.append(r)
            elif nv: rules.append(r)
        img += self.imgs
        groups = []; cur = []
        for i, l in enumerate(body):
            inrule = any(r.y0 - 4 < l['y'] < r.y1 + 6 and r.x0 > l['x0'] and r.x1 < l['x1'] for r in rules)
            if l['tab'] or inrule:
                l['tab'] = True
                if cur and l['y'] - cur[-1]['y'] > 30:
                    groups.append(cur); cur = []
                cur.append(l)
            elif cur:
                nxt = next((m for m in body[i + 1:] if m['tab']), None)
                if nxt and nxt['y'] - cur[-1]['y'] < 45 and l['x1'] - l['x0'] < 200 and not l['x1'] > self.R - 12:
                    cur.append(l)
                else:
                    groups.append(cur); cur = []
        if cur: groups.append(cur)
        cols = []
        for gl in groups:
            r = fitz.Rect(min(l['x0'] for l in gl), min(l['y'] - l['size'] for l in gl), max(l['x1'] for l in gl), max(l['y'] + 3 for l in gl))
            hit = [k for k, o in enumerate(img) if (o + (-4, -14, 4, 14)).intersects(r)]
            if hit:
                for k in hit: img[k] = runion(img[k], r)
                continue
            # 번호 목록을 두 단으로 놓은 것('① 믿음 … ⑦ 바른 말') → 글로 (뒤에 붙은 번호 줄도 함께)
            k = body.index(gl[-1]) + 1
            while k < len(body) and body[k]['y'] - gl[-1]['y'] < 30 and len(self.mcells(body[k])) >= 2: gl.append(body[k]); k += 1
            if len(gl) == 1 and len(self.mcells(gl[0])) >= 2:
                continue   # 한 줄짜리 번호 줄('⑦ 어머니가 있다 ⑧ 아버지가 있다')은 인쇄된 그대로 글로
            if all(len(self.mcells(l)) >= 2 for l in gl):
                r = fitz.Rect(min(l['x0'] for l in gl), min(l['y'] - l['size'] for l in gl), max(l['x1'] for l in gl), max(l['y'] + 3 for l in gl))
                cols.append((r, gl))
            else:
                for h in self.hl:
                    if h.y0 > r.y0 - 16 and h.y1 < r.y1 + 16 and h.x0 < r.x1 and h.x1 > r.x0: r = runion(r, h)
                img.append(r)
        img = merge_rects(img, 3)
        # 위아래로 붙은 표 조각(머리 줄·몸통)은 하나로
        merged = True
        while merged:
            merged = False
            for a in range(len(img)):
                for b in range(len(img)):
                    if a != b and img[a].x0 < img[b].x1 and img[b].x0 < img[a].x1 and 0 <= img[b].y0 - img[a].y1 < 40 and \
                            not any(img[a].y1 < l['y'] < img[b].y0 and l['x1'] > self.R - 15 for l in body):
                        img[a] = runion(img[a], img[b]); del img[b]; merged = True; break
                if merged: break
        for _ in range(4):
            ch = False
            for k, r in enumerate(img):
                for l in body:
                    if r.y0 - 2 < l['y'] < r.y1 + 3 and not (l['x0'] >= r.x0 - 1 and l['x1'] <= r.x1 + 1):
                        if (l['x1'] < self.R - 15 and l['x1'] - l['x0'] < 150) or l['tab'] or (l['x0'] > r.x0 - 30 and l['x1'] < r.x1 + 30):
                            img[k] = runion(r, fitz.Rect(l['x0'], l['y'] - l['size'], l['x1'], l['y'] + 3)); ch = True
            img = merge_rects(img, 2)
            if not ch: break
        # 표 바로 위아래의 표 글(맨 아래 줄 '존재 | 인간…', 왼쪽 이름 칸·오른쪽 풀이 칸이 나뉜 표) 도 그림에
        for _ in range(12):
            ch = False
            for k, r in enumerate(img):
                for l in body:
                    if r.y0 - 2 <= l['y'] <= r.y1 + 3 and r.x0 - 1 <= l['x0'] and l['x1'] <= r.x1 + 1: continue
                    near = r.y0 - 30 < l['y'] < r.y1 + 30
                    full = l['x1'] > self.R - 12 and l['x0'] < self.L + 12
                    inside_x = l['x0'] >= r.x0 - 2 and l['x1'] <= r.x1 + 2
                    rightcol = l['x0'] >= self.L + 60 and abs(l['x1'] - r.x1) < 15
                    leftlab = l['x0'] < self.L + 15 and l['x1'] - l['x0'] < 70
                    vis = [c for c in l['cs'] if c['c'].strip() and re.match(r'[가-힣A-Za-z]', c['c'])]
                    allbold = vis and sum(c['bold'] for c in vis) >= len(vis) * 0.8
                    above = l['y'] < r.y0
                    if above and (allbold or re.search(r'[.:：]\s*$', l['text']) or l['x1'] - l['x0'] > 150 or any(c.get('sup') for c in l['cs'])) and not l['tab']: continue
                    if near and not full and (inside_x or rightcol or leftlab) and not re.match(r'\s*(?:\*\*)?표\s', l['text']) and l['size'] < 11:
                        img[k] = runion(img[k], fitz.Rect(l['x0'], l['y'] - l['size'], l['x1'], l['y'] + 3)); r = img[k]; ch = True
            img = merge_rects(img, 2)
            if not ch: break
        img = [r for r in img if r.width > 20 and r.height > 8]
        cols = [(r, gl) for r, gl in cols if not any(o.intersects(r) for o in img)]
        return img, cols

    def cell_chars(self, l):
        out = [[]]
        thr = max(18, 2.2 * l['size']); prev = None
        vls = [v for v in self.vl if v.y0 - 4 < l['y'] < v.y1 + 6]
        for c in l['cs']:
            if prev is not None and c['c'].strip() and (c['x'] - prev['x1'] > thr or any(prev['x1'] <= v.x0 <= c['x'] for v in vls)
                                                         or (re.match(r'[①-⑳]', c['c']) and c['x'] - prev['x1'] > 4)):
                out.append([])
            out[-1].append(c)
            if c['c'].strip(): prev = c
        return [x for x in out if ''.join(c['c'] for c in x).strip()]

    def mcells(self, l):
        """번호(①, 1), 13) …)마다 나눈 칸 — 줄이 번호로 시작하고 번호가 둘 이상일 때만"""
        txt = ''.join(c['c'] for c in l['cs'])
        if not MARK.match(txt): return []
        out = [[]]; prev = None
        for c in l['cs']:
            if prev is not None and ((re.match(r'[①-⑳㉑-㉟]', c['c']) and c['x'] - prev['x1'] > -0.5) or c['x'] - prev['x1'] > 4 and (re.match(r'\d', c['c']) and re.match(r'\d{1,2}\)', ''.join(x['c'] for x in l['cs'][l['cs'].index(c):l['cs'].index(c) + 3])))):
                out.append([])
            out[-1].append(c)
            if c['c'].strip(): prev = c
        out = [x for x in out if ''.join(c['c'] for c in x).strip()]
        return out if len(out) >= 2 else []

    def cells(self, l):
        return [''.join(c['c'] for c in x).strip() for x in self.cell_chars(l)]


HANG = re.compile(r'[\w가-힣]')
LAT = re.compile(r'[A-Za-zĀ-ſḀ-ỿ]')


def markup(cs, refs=True, bold=True, ital=True):
    """글자들 → 글 (각주 번호 [^n], 굵게 **, 기울임 °°)"""
    n = len(cs)
    B = [bool(bold and c['bold'] and not c.get('sup')) for c in cs]
    for i, c in enumerate(cs):
        if not HANG.match(c['c']) and not c.get('sup'):
            a = next((B[j] for j in range(i - 1, -1, -1) if HANG.match(cs[j]['c'])), None)
            z = next((B[j] for j in range(i + 1, n) if HANG.match(cs[j]['c'])), None)
            B[i] = (a is not False) and (z is not False) and not (a is None and z is None)
    I = [bool(ital and c['ital'] and not c.get('sup') and not B[i]) for i, c in enumerate(cs)]
    for i, c in enumerate(cs):
        if not LAT.match(c['c']) and I[i]:
            a = next((I[j] for j in range(i - 1, -1, -1) if LAT.match(cs[j]['c'])), False)
            z = next((I[j] for j in range(i + 1, n) if LAT.match(cs[j]['c'])), False)
            I[i] = a and z
    out = []; i = 0
    while i < n:
        c = cs[i]
        if c.get('sup'):
            j = i
            while j < n and cs[j].get('sup'): j += 1
            s = ''.join(x['c'] for x in cs[i:j])
            out.append(re.sub(r'(\d+)\)', lambda m: f'[^{m.group(1)}]', s) if refs else s); i = j; continue
        if B[i] or I[i]:
            key = B if B[i] else I; mk = '**' if B[i] else '°°'
            j = i
            while j < n and key[j] and not cs[j].get('sup'): j += 1
            s = ''.join(x['c'] for x in cs[i:j])
            if HANG.search(s) or re.search(r'[A-Za-z0-9]', s):
                a = s[:len(s) - len(s.lstrip())]; z = s[len(s.rstrip()):]
                out.append(a + mk + s.strip() + mk + z)
            else: out.append(s)
            i = j; continue
        ch = c['c']
        if ch == '*' and ((i + 1 < n and cs[i + 1]['c'] == '*') or (i and cs[i - 1]['c'] == '*')): ch = '∗'   # 책에 찍힌 '**' (굵게 표시와 헷갈리지 않게)
        out.append(ch); i += 1
    t = ''.join(out)
    t = t.replace('　', ' ')
    t = re.sub(r'\*\*(\s*)\*\*', r'\1', t)
    t = re.sub(r'°°(\s*)°°', r'\1', t)
    return t


def refy(P, regs, L):
    """표 아래에서 각주 'N)' 로 시작하는 작은 글씨 줄을 찾아 각주 구분 자리로"""
    bot = max(r.y1 for r in regs)
    for l in sorted(L, key=lambda l: l['y']):
        if l['y'] > bot + 2 and l['size'] < 9.6 and re.match(r'\s*\d+\)', l['text']) and l['x0'] < P.L + 4:
            return l['y'] - l['size'] - 1
    # 'N)' 이 없으면(앞 쪽에서 이어진 각주) 표 아래 작은 글씨 줄
    for l in sorted(L, key=lambda l: l['y']):
        if l['y'] > bot + 2 and l['size'] < 9.6 and l['zone'] != 'foot':
            return l['y'] - l['size'] - 1
    return None
