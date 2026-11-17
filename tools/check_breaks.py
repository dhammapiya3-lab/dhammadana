#!/usr/bin/env python3
"""본문 끊김 검사 (운영자 요청, 2026-11-18 — 지침): PDF·한글 파일에서 뽑은 본문에서 자주 생기는 두 가지를 찾는다.
  python3 tools/check_breaks.py [책 ID…] [--all]   (책 ID 를 안 주면 모든 책, 목록은 처음 몇 곳만 — --all 이면 모두)
① 넘친 각주: 쪽 아래 각주가 문장 중간에서 끝났는데(…산스 / …때문), 다음 쪽 본문 문단 가운데 그 이어지는 글이 들어가 있는 것
   → 각주 끝에 이어 붙여야 함 (예: DL-0012 26쪽 각주 4 — tools/dl0012_fn_overflow.py)
② 끊긴 문단: 한 쪽 안에서 문장 중간(…명상 지도자는 / 보고하는 말을…, …주의해서 듣 / 고)에 빈 줄이 들어가 문단이 둘로 나뉜 것
   — 매달린 들여쓰기(• 항목·번호 목록의 둘째 줄)를 새 문단으로 잘못 본 경우가 많음 → 이어 붙여야 함 (예: tools/dl0012_bullet_join.py)
게송·독송문(++ ), 가운데·오른쪽 맞춤(:: >> ^^), 차례(%% ), 표(|), 제목(## ), 그림·각주 줄은 줄 나눔이 원래 모양이라 보지 않는다.
찾은 것은 '확인할 곳'이다 — 인쇄본(PDF)과 대조해서 실제로 끊긴 곳만 고친다. 글자는 바꾸지 않고 빈 줄·자리만 바로잡는다."""
import json, re, sys, glob, os, signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
END = re.compile(r'[.?!。…:;)\]」』”’"\'>*=°§@}~]\s*$|다\s*$|요\s*$|음\s*$|함\s*$|임\s*$|됨\s*$|짐\s*$|참조\s*$|참고\s*$|\d\s*$')
SKIP = ('++', '::', '>>', '^^', '%%', '|', '##', '![', '[^', '~', '||', '@@', '°°', '{{', '§§', '[[')
LINES = {'DL-0026', 'DL-0031'}   # 인쇄본 줄을 그대로 두는 독송집 — ② 는 보지 않음
def plain(s): return re.sub(r'\*\*|==|°°|§§|@@|\{\{|\}\}', '', s).strip()
def check(bk, show):
    p = f'content/texts/{bk}.json'
    if not os.path.exists(p): return 0, 0
    T = json.load(open(p)); parts = re.split(r'\n?(=== [^\n]*===)\n?', T['body'])
    P = [(parts[i], parts[i + 1]) for i in range(1, len(parts), 2)]
    A, B = [], []
    for i, (name, t) in enumerate(P):
        paras = [x.strip() for x in re.split(r'\n\s*\n', t) if x.strip()]
        body = [x for x in paras if not x.startswith('[^')]
        # ② 끊긴 문단 (같은 쪽 안)
        for a, b in (zip(body, body[1:]) if bk not in LINES else []):
            if a.startswith(SKIP) or b.startswith(SKIP) or b.startswith(('•', '●', '-', '*', '(', '[', '“', '‘', '「', '『')): continue
            if re.match(r'^(\d+|[①-⑳㉑-㊿]|[가-하]|[IVXⅠ-Ⅻ]+)[.)\s]', b): continue
            la = plain(a.split('\n')[-1]); fb = plain(b)
            if not la or not fb or END.search(la) or len(la) < 25: continue   # 짧은 줄(제목·게송·판권 줄)은 원래 끝나는 줄
            if re.match(r'^\S[^:：]{0,40}\s[:：]\s', fb) or re.search(r'\s[:：]\s', la[:45]): continue   # 용어 풀이 '낱말 : 풀이' 줄
            if a.count('\n') >= 2 and len(a.split('\n')[0]) < 25: continue   # 줄마다 끊어 쓴 묶음(독송문 등)
            if re.search(r'[가-힣A-Za-zāīūṃṅñṭḍṇḷ,]$', la) and re.match(r'[가-힣a-zāīūṃṅñṭḍṇḷ]', fb):
                B.append(f'{name.strip("= ")}: …{la[-18:]} / {fb[:18]}…')
        # ① 넘친 각주 (다음 쪽 본문 가운데 각주에서 이어지는 글이 있는지)
        fns = [x for x in paras if x.startswith('[^')]
        if fns and i + 1 < len(P):
            last = plain(fns[-1].split('\n')[-1])
            if not END.search(last):
                nxt = [x.strip() for x in re.split(r'\n\s*\n', P[i + 1][1]) if x.strip() and not x.strip().startswith('[^')]
                cand = [x for k, x in enumerate(nxt) if k and re.match(r'[가-힣a-zāīūṃṅñṭḍṇḷ(④-⑳]', plain(x)) and not x.startswith(SKIP)
                        and (not END.search(plain(nxt[k - 1].split('\n')[-1])) or k == len(nxt) - 1)]
                if cand:
                    A.append(f'{name.strip("= ")} 각주 {re.match(r"\[\^([^\]]+)\]", fns[-1]).group(1)}: …{last[-16:]} → 다음 쪽 본문 속 "{plain(cand[0])[:22]}…"')
    if A or B:
        print(f'■ {bk} ({T.get("title", "") or ""}) — ① 넘친 각주 의심 {len(A)} · ② 끊긴 문단 의심 {len(B)}')
        for x in (A if show else A[:5]): print('   ①', x)
        for x in (B if show else B[:8]): print('   ②', x)
        if not show and (len(A) > 5 or len(B) > 8): print('   … (모두 보려면 --all)')
    return len(A), len(B)
args = [a for a in sys.argv[1:] if not a.startswith('--')]; show = '--all' in sys.argv
books = args or sorted(os.path.basename(f)[:-5] for f in glob.glob('content/texts/DL-*.json'))
ta = tb = 0
for bk in books:
    a, b = check(bk, show); ta += a; tb += b
print(f'모두: ① 넘친 각주 의심 {ta} · ② 끊긴 문단 의심 {tb}' + ('  — 없음 ✓' if not (ta or tb) else '  — 인쇄본과 대조해 실제로 끊긴 곳만 고칠 것'))
