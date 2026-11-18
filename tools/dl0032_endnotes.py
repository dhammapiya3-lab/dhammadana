#!/usr/bin/env python3
"""『빠릿따 독송예경문』(DL-0032) 미주(303쪽~) — 쪽을 넘어간 미주 글이 다음 쪽 보통 문단으로
들어가 있던 것을 앞 미주 끝에 이어 붙임 (운영자 요청, 2026-11-18 '가) 미주 안으로 옮기기').
쪽 표시(=== N쪽 ===)는 그대로 두므로 미주 글만 이어지던 쪽(306~310쪽 등)은 쪽 이름만 남음.
이어 붙일 때: 앞 글이 문장·괄호 끝(. ) 」 ” :)이면 줄 바꿈, 아니면 빈칸 하나 — 낱말 가운데에서
쪽이 넘어간 곳은 JOIN 에 적어 빈칸 없이. 글자는 그대로.
  python3 tools/dl0032_endnotes.py [--write] [--show]   (pdf2text_dl0032.py 로 본문을 다시 만들면 다시 돌림)"""
import json, re, sys, collections
F = 'content/texts/DL-0032.json'
JOIN = [('불안으로부', '터 자유'), ('닦아야 합', '니다.'), ('다섯 번', '째와'), ('습관적으로 원', '전을'), ('그것들을 철', '저히'), ('삼장 형태로 전', '해오고'), ('자신감 있', '고 행복'), ('둘러싸여 다', '음 생의'), ('수명은 2000년', '이다'), ('인도한다', '는 뜻'), ('제따 왕자', '로부터'), ('그 자신', '의 부모'), ('① 스', '승(붓다)'), ('열심히 정진하', '도록'), ('다음 생', '의 이익'), ('보디삿', '따(미래'), ('상수 제자', '인 사리뿟따'), ('여자가 없고 남', '자가 없고'), ('‘혐오스', '러운-'), ('즐거운 느', '낌이 일어남'), ('세상에 도', '달하기'), ('현명한 반조', '와 본삼매'), ('진리에 대한 지혜', '입니다.'), ('지각, 느', '낌을 뺀'), ('취착, 상', '카라, 업이'), ('만드는 유익', '하고 해로운'), ('(갈마)로 대체', '했습니다.'), ('와(va) 케미노', '(khemino)')]  # (앞 글 끝, 다음 글 첫머리) — 쪽이 낱말 가운데에서 넘어가 빈칸 없이 붙일 곳 (2026-11-18 하나씩 확인)
d = json.load(open(F)); body = d['body']
k0 = body.find('=== 303쪽 ===')
head, tail = body[:k0], body[k0:]
parts = re.split(r'(\n*=== [^=\n]* ===\n*)', tail)
paras = []   # [(part index, list)]
for i, x in enumerate(parts):
    if not re.match(r'\n*===', x): paras.append((i, [p for p in x.split('\n\n')]))
last = None; moved = 0; show = []
for pi, (i, pa) in enumerate(paras):
    keep = []; first = True
    for p in pa:
        s = p.strip()
        if not s or s.startswith('[^') or s.startswith('#') or last is None:
            keep.append(p)
            if s.startswith('[^'): last = (pi, len(keep) - 1)
            continue
        li, lj = last
        tgt = paras[li][1] if li != pi else keep
        prev = tgt[lj].rstrip()
        cross = li != pi and first; first = False
        if not cross or re.search(r'[.)」”:’]$', prev): sep = '\n'
        elif any(prev.endswith(a) and s.startswith(b) for a, b in JOIN): sep = ''
        else: sep = ' '
        show.append(('쪽' if cross else '  ', prev[-20:], sep, s[:20]))
        tgt[lj] = prev + sep + s
        if li == pi: last = (pi, lj)
        moved += 1
    pa[:] = keep
for i, pa in paras:
    lead = re.match(r'\n*', parts[i]).group(); trail = parts[i][len(parts[i].rstrip('\n')):]
    parts[i] = '\n\n'.join(pa) if pa else ''
new = head + ''.join(parts)
c = lambda t: collections.Counter(re.sub(r'\s', '', t))
assert c(new) == c(body), '글자가 달라짐'
print('옮긴 문단', moved, '· 쪽을 넘어 이은 곳', sum(1 for w,*_ in show if w == '쪽'), '· 빈칸 없이', sum(1 for w,a,sep,b in show if w == '쪽' and sep == ''))
if '--show' in sys.argv:
    for w, a, sep, b in show:
        if sep != '\n': print(w, repr(a), {' ': '␣', '': '·'}[sep], repr(b))
if '--write' in sys.argv:
    d['body'] = new
    raw = open(F).read(); ind = 2 if raw.startswith('{\n  ') else None
    open(F, 'w').write(json.dumps(d, ensure_ascii=False, indent=ind) + ('\n' if raw.endswith('\n') else ''))
    print('저장함')
