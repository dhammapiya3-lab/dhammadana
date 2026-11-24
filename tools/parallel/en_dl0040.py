#!/usr/bin/env python3
"""DL-0040『위빠싸나 성자 아짠 문』 원서 글 뽑기 — The Venerable Phra Acharn Mun Bhuridatta Thera, Meditation Master
(Compiled by Phra Acharn Maha Boowa Ñāṇasampanno, translated into English by M. Siri Buddhasukh, 1976;
electronic transcription of the second printing (1982) by Ong Lee Lin, Li Chun and Paul Trafford, 3 April 2002 —
Word 9.0 → Acrobat Distiller PDF 238쪽, 쪽 번호가 인쇄되지 않음 — 차례의 쪽 번호가 PDF 쪽과 같아 PDF 쪽 = 쪽 이름).

  python3 tools/parallel/en_dl0040.py 원서.pdf   →  tools/out/parallel/DL-0040.en.paras.json

조판: CenturyGothic 10pt, 문단 사이에 빈 줄(빈칸만 있는 줄) — 빈 줄에서 새 문단, 줄은 빈칸으로 이어 붙임(줄 끝 '-' 는
겹낱말이 줄 끝에서 나뉜 것이라 빈칸 없이). 빈 줄 없이 들여쓰기가 바뀌며 번호·글자 항목('1. ' 'a. ' '1-2. ')으로
시작하는 줄도 새 문단. 같은 높이(3pt 안)에 놓인 조각('f.' + 항목 글)은 한 줄로. 쪽이 넘어갈 때 앞 쪽 끝에 빈 줄이
없으면 문단을 이어 붙임. 제목: 굵은 14pt(이어진 줄은 한 제목) → 'h', 보충주 제목 굵은 12pt → 'h'.
각주: 쪽 아래 Verdana 구분선 아래, 6pt 번호로 시작하는 줄이 새 각주 → 'fn' '[^N]: …'(쪽을 넘으면 이어 붙임),
본문 속 6~6.5pt 숫자 → [^N]. 1쪽 속표지 → 제목·지은이 'h'/'p', 5~10쪽 차례 → 'toc'(점선 뒤 쪽 번호 남김).
글자는 PDF 글자 그대로(줄 끝 빈칸·각주 번호 모양만 다름).
"""
import json, os, re, sys
import fitz

PDF = sys.argv[1]
OUT = os.path.join(os.path.dirname(__file__), '..', 'out', 'parallel', 'DL-0040.en.paras.json')
doc = fitz.open(PDF)
LIST = re.compile(r'^(\d+(-\d+)?\.|[a-j]\.)\s')

def lines_of(page):
    """[(y, x0, x1, text, kind)] kind: 'b' 본문 'h14' 'h12' 'fnstart' 'fn' 'sep'"""
    out = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = l['spans']
            if not sp: continue
            out.append([l['bbox'][1], l['bbox'][0], l['bbox'][2], sp])
    out.sort(key=lambda r: (round(r[0]), r[1]))
    # 같은 높이 조각은 한 줄로
    merged = []
    for r in out:
        if merged and abs(merged[-1][0] - r[0]) < 3 and r[1] >= merged[-1][2] - 2:
            merged[-1][2] = r[2]; merged[-1][3] = merged[-1][3] + [{'text': ' ', 'size': 10, 'font': 'x'}] + r[3]
        else: merged.append(r)
    return merged

LASTFN = [0]
def span_text(sp, body=True):
    t = ''
    for s in sp:
        x = s['text']
        if body and s['size'] < 7 and re.fullmatch(r'\s*\d+\s*', x) and t.strip():
            n = x.strip()
            if int(n) != LASTFN[0] + 1 and len(n) % 2 == 0 and n[:len(n)//2] == n[len(n)//2:]: n = n[:len(n)//2]   # 153쪽 '3838' — 번호가 두 번 찍힘
            LASTFN[0] = int(n)
            t += '[^%s]' % n; continue
        t += x
    return t

paras = []   # {'pg','k','t'}
cur = None   # 열린 본문 문단
fn_cur = None
def close():
    global cur
    if cur and cur['t'].strip():
        cur['t'] = re.sub(r'[  ]+', ' ', cur['t']).strip(); paras.append(cur)
    cur = None
def add(pg, k, t):
    close(); paras.append({'pg': pg, 'k': k, 't': re.sub(r'[  ]+', ' ', t).strip()})
def join(a, b):
    a = a.rstrip()
    if a.endswith('-') and not a.endswith(' -'): return a + b.lstrip()
    return a + ' ' + b.lstrip()

for pn in range(doc.page_count):
    pg = pn + 1
    L = lines_of(doc[pn])
    if pg <= 11: close()   # 앞쪽 글·차례·본문 첫 쪽은 쪽마다 따로
    if pg == 1:
        tt = [span_text(r[3], False).strip() for r in L if span_text(r[3], False).strip()]
        add(pg, 'h', tt[0] + ' ' + tt[1]); add(pg, 'p', tt[2])
        add(pg, 'p', ' '.join(tt[3:-1])); add(pg, 'pq', tt[-1]); continue
    if 5 <= pg <= 10:
        for r in L:
            t = span_text(r[3], False).strip()
            if not t: continue
            if cur is not None and not re.search(r'\.{3,}\s*\d+$', cur['t']):
                cur['t'] = join(cur['t'], t)
            else:
                close(); cur = {'pg': pg, 'k': 'toc', 't': t}
            if re.search(r'\.{3,}\s*\d+$', cur['t']): close()
        close(); continue
    # 각주 구역: Verdana 구분선 아래
    sep_y = None
    for r in L:
        if r[3][0]['font'].startswith('Verdana'): sep_y = r[0]
    blank_before = True if cur is None else False
    prev_x0 = None
    hbuf = None   # 이어지는 제목 줄 [y, kind, text]
    for r in L:
        y, x0, x1, sp = r
        f = sp[0]
        raw = ''.join(s['text'] for s in sp)
        if sep_y is not None and y >= sep_y:
            if f['font'].startswith('Verdana'): continue
            if not raw.strip(): continue
            t = span_text(sp, False).strip()
            m = re.match(r'^(\d+)\s+(.*)$', t)
            if f['size'] < 7 and m:
                if fn_cur: paras.append(fn_cur)
                fn_cur = {'pg': pg, 'k': 'fn', 't': '[^%s]: %s' % (m.group(1), m.group(2))}
            elif fn_cur:
                fn_cur['t'] = join(fn_cur['t'], t)
            continue
        if not raw.strip():
            if hbuf: add(pg, 'h', hbuf[2]); hbuf = None
            close(); blank_before = True; continue
        bold = 'Bold' in f['font']
        big = bold and f['size'] >= 11.5 and all(('Bold' in s['font']) or not s['text'].strip() for s in sp)
        if big:
            t = raw.strip()
            if hbuf and y - hbuf[0] < 25: hbuf[2] += ' ' + t; hbuf[0] = y
            else:
                if hbuf: add(pg, 'h', hbuf[2])
                close(); hbuf = [y, 'h', t]
            continue
        if hbuf: add(pg, 'h', hbuf[2]); hbuf = None
        t = span_text(sp)
        if cur is None:
            cur = {'pg': pg, 'k': 'p', 't': t}
        elif LIST.match(t.strip()) and prev_x0 is not None and abs(x0 - prev_x0) > 5:
            close(); cur = {'pg': pg, 'k': 'p', 't': t}
        else:
            cur['t'] = join(cur['t'], t)
        prev_x0 = x0; blank_before = False
    if hbuf: add(pg, 'h', hbuf[2]); hbuf = None
    # 쪽 끝: 문단은 다음 쪽에서 이어질 수 있으므로 닫지 않음 (빈 줄로 끝났으면 이미 닫힘)
    # 각주 문단은 다음 쪽에 이어질 수 있음 — 다음 쪽 각주 구역 첫 줄이 번호 없이 시작하면 이어 붙임
close()
if fn_cur: paras.append(fn_cur)

# 각주 문단은 처음 가리키는 본문 문단 바로 뒤로 (한국어 각주 짝짓기 순서와 맞게)
body = [p for p in paras if p['k'] != 'fn']; fns = [p for p in paras if p['k'] == 'fn']
out = []
placed = set()
fnmap = {re.match(r'\[\^(\d+)\]', f['t']).group(1): f for f in fns}
for p in body:
    out.append(p)
    for n in re.findall(r'\[\^(\d+)\]', p['t']):
        if n in fnmap and n not in placed: out.append(fnmap[n]); placed.add(n)
for n, f in fnmap.items():
    if n not in placed: print('각주 자리 못 찾음', n); out.append(f)
for p in out: p['t'] = p['t'].replace(' ', ' ')
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=0)
from collections import Counter
print('문단', len(out), Counter(p['k'] for p in out))
