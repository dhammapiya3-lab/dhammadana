#!/usr/bin/env python3
"""모든 책 '온라인으로 읽기' 본문 구조 검사 (운영자 요청, 2026-11-18 '다시 검수해줘').
인쇄본 PDF 없이 본문 파일만으로 찾을 수 있는 것을 모두 본다. 찾은 것은 '확인할 곳' — 고칠지는 하나씩 보고 정한다.
  python3 tools/audit_all.py [책 ID…] [--all]
① 각주: 본문에 번호는 있는데 풀이가 없음 / 풀이는 있는데 본문에 번호가 없음 / 같은 번호 풀이가 둘 / 빈 풀이
② 표시 짝: 한 문단 안에서 ** °° @@ == §§ 가 홀수, {{ }} 짝이 안 맞음
③ 쪽 이름: 숫자 쪽 이름이 1씩 늘지 않음(건너뜀·되돌아감)
④ 목차(쪽은 1부터 센 순번): 쪽 순번이 범위를 벗어남, at(쪽 중간 시작) 글을 그 쪽에서 못 찾음
⑤ 그림: 본문·images 의 /uploads/ 파일이 없음
⑥ 글자: 깨진 글자(U+FFFD)·사용자 정의 글자(U+E000~F8FF)·보이지 않는 글자(ZWSP·소프트 하이픈·제어 문자)·전각 ASCII·구분 막대 ㅣ │ ｜
⑦ 로마자 줄 끝 하이픈이 남은 것('abhab- ba')
⑧ 문장 중간에서 끊겨 다음 줄이 소제목(## )이 된 것 (예: DL-0031 판권지 '…저자의 / ## 허락 없이 출간하실 수 있습니다.' — 운영자가 2026-11-18 관리 화면에서 고침)
"""
import json, re, sys, glob, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
MK = re.compile(r'\*\*|__|==|°°|§§|@@|\{\{|\}\}')
def plain(s): return MK.sub('', s)
PUA_OK = {'DL-0018'}   # PaliHangul 은 ph 사전에만 — 본문에는 없어야 하지만 혹시 있으면 알림
def audit(bk):
    T = json.load(open(f'content/texts/{bk}.json')); b = T['body']; out = collections.defaultdict(list)
    parts = re.split(r'\n?(=== [^\n]*===)\n?', b)
    P = [(parts[i].strip('= ').strip(), parts[i + 1]) for i in range(1, len(parts), 2)]
    # ① 각주
    defs = collections.Counter(m.group(1) for m in re.finditer(r'(?m)^\[\^([^\]\s]+)\]:', b))
    refs = set(m.group(1) for m in re.finditer(r'(?m)(?<!^)(?<!^[ \t])\[\^([^\]\s]+)\]', b))   # 줄 첫머리가 아니면 ':' 가 붙어도 본문 번호 (app.js fnMark 와 같음)
    for k, n in defs.items():
        if n > 1: out['① 같은 번호 풀이가 여럿'].append(f'[^{k}] × {n}')
    for k in sorted(refs - set(defs), key=lambda x: (len(x), x)): out['① 번호만 있고 풀이 없음'].append(f'[^{k}]')
    for k in sorted(set(defs) - refs, key=lambda x: (len(x), x)): out['① 풀이만 있고 본문 번호 없음'].append(f'[^{k}]')
    for m in re.finditer(r'(?m)^\[\^([^\]\s]+)\]:[ \t]*$', b): out['① 빈 풀이'].append(f'[^{m.group(1)}]')
    # ② 표시 짝
    ULB = re.search(r'__(?=[^_\s])[^\n]*?[^_\s]__', b) is not None
    for name, t in P:
        for para in re.split(r'\n\s*\n', t):
            if para.startswith('|'): continue
            for mk in ('**', '__', '°°', '@@', '==', '§§'):
                if mk == '__' and not ULB: continue   # 밑줄 표시 __…__ 를 쓰는 책만 (다른 책의 '___' 는 인쇄된 글자)
                c = para.count(mk)
                if c % 2: out[f'② {mk} 짝 안 맞음'].append(f'{name}: {plain(para)[:40]}…')
            if para.count('{{') != para.count('}}'): out['② {{ }} 짝 안 맞음'].append(f'{name}: {plain(para)[:40]}…')
    # ③ 쪽 이름
    prev = None
    for name, _ in P:
        m = re.fullmatch(r'(\d+)(?:~(\d+))?쪽', name)   # '18~19쪽' 펼친 쪽도 셈
        if not m: continue
        n = int(m.group(1)); e = int(m.group(2) or n)
        if prev is not None and n not in (prev, prev + 1):
            out['③ 쪽 번호가 1씩 늘지 않음'].append(f'{prev}쪽 → {n}쪽')
        prev = e
    # ④ 목차
    for e in T.get('toc', []):
        pg = e.get('page')
        if not isinstance(pg, int) or pg < 1 or pg > len(P):
            out['④ 목차 쪽 순번이 범위 밖'].append(f"{e.get('title')} ({pg})"); continue
        at = str(e.get('at') or '').strip()
        if at:
            txt = re.sub(r'\s+', '', plain(P[pg - 1][1])); a = re.sub(r'\s+', '', plain(at))
            if a not in txt: out['④ 목차 at 글을 그 쪽에서 못 찾음'].append(f"{e.get('title')} — '{at[:20]}' ({P[pg - 1][0]})")
    # ⑤ 그림
    imgs = set(re.findall(r'\]\((/uploads/[^)\s]+)\)', b))
    for x in T.get('images', []): imgs.add(x['image'] if isinstance(x, dict) else x)
    for u in sorted(imgs):
        if u.startswith('/uploads/') and not os.path.exists('public' + u): out['⑤ 그림 파일 없음'].append(u)
    for x in T.get('images', []):
        if not isinstance(x, dict) or not x.get('image'): out['⑤ images 모양이 {image, caption} 이 아님'].append(str(x)[:40])
    # ⑥ 글자
    for name, t in P:
        for ch, lab in (('�', '깨진 글자 U+FFFD'), ('​', '보이지 않는 글자 ZWSP'), ('­', '소프트 하이픈'), ('﻿', 'BOM')):
            if ch in t: out['⑥ ' + lab].append(f'{name}: …{t[max(0, t.find(ch) - 12):t.find(ch) + 6]}…'.replace('\n', '⏎'))
        for m in re.finditer(r'[-]', t): out['⑥ 사용자 정의 글자(PUA)'].append(f'{name}: U+{ord(m.group()):04X} …{t[max(0, m.start() - 8):m.start() + 4]}…'.replace('\n', '⏎'))
        for m in re.finditer(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', t): out['⑥ 제어 문자'].append(f'{name}: U+{ord(m.group()):04X}')
        for m in re.finditer(r'[！-～]', t): out['⑥ 전각 ASCII'].append(f'{name}: {m.group()} …{t[max(0, m.start() - 8):m.start() + 6]}…'.replace('\n', '⏎'))
        for m in re.finditer(r'(?<=\S) [ㅣ│｜] (?=\S)', t): out['⑥ 구분 막대가 | 가 아님'].append(f'{name}: …{t[max(0, m.start() - 10):m.end() + 8]}…'.replace('\n', '⏎'))
    # ⑦ 로마자 줄 끝 하이픈
    for name, t in P:
        for m in re.finditer(r'\b([A-Za-zāīūṃṁṅñṭḍṇḷ]{2,})- ([a-zāīūṃṁṅñṭḍṇḷ]{2,})', t):
            out['⑦ 로마자 사이 "- " (줄 끝 하이픈이 남았는지)'].append(f'{name}: {m.group()}')
    # ⑧ 문장 중간에서 끊겨 소제목이 된 줄
    END = re.compile(r'[.?!。…:;)\]」』”’"\'>*=°§@}~|]\s*$|다\s*$|요\s*$|\d\s*$')
    for name, t in P:
        paras = [x.strip() for x in re.split(r'\n\s*\n', t) if x.strip()]
        for a, h in zip(paras, paras[1:]):
            if not h.startswith('## ') or a.startswith(('#', '%%', '|', '![', '^^', '::', '>>', '[^', '~')): continue
            la = plain(a.split('\n')[-1]).strip()
            if len(la) >= 12 and not END.search(la) and re.search(r'[가-힣a-z,]$', la):
                out['⑧ 문장 중간에서 끊겨 다음 줄이 소제목'].append(f'{name}: …{la[-16:]} / {plain(h)[:24]}')
    return out
def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; full = '--all' in sys.argv
    bks = a or sorted(os.path.basename(f)[:-5] for f in glob.glob('content/texts/*.json'))
    tot = 0
    for bk in bks:
        r = audit(bk); n = sum(len(v) for v in r.values()); tot += n
        if not n: continue
        print(f'■ {bk} — {n}')
        for k, v in r.items():
            print(f'  {k} ({len(v)})')
            for x in (v if full else v[:6]): print('     ', x)
            if not full and len(v) > 6: print(f'      … 외 {len(v) - 6}')
    print(f'모두 {tot}곳 (확인할 곳)')
if __name__ == '__main__': main()
