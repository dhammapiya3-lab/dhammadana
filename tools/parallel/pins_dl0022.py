"""DL-0022 원서 대조 손 짝 만들기 — run_dl0022.sh 가 부름 (한 줄에 인자 하나).
경마다: 한국어 경 제목 ↔ 원서 경 제목 두 줄(--pin·--seg), 단락 번호(한국어 **N** ↔ 원서 단락 N — en_dl0022 의 sec,
OCR 경은 'N. ' 첫머리)가 경 안에서 양쪽 모두 하나뿐이면 --seg(경계).
원서 짝 자료에 없는 경(ONLY_SC 로 뺀 7개 경)은 한국어 쪽을 --ko-skip."""
import os, re, json
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = json.load(open(os.path.join(REPO, 'content/texts/DL-0022.json')))
O = json.load(open(os.path.join(REPO, 'tools/out/parallel/DL-0022.en.paras.json')))
ORDER = [26, 4, 36, 95, 135, 41, 61, 21, 63, 29, 27, 39, 19, 20, 7, 8, 2, 112, 152, 105, 10, 118, 9, 38, 148, 149]
body = T['body'].replace('\r\n', '\n')
ms = list(re.finditer(r'^===\s*(.*?)\s*===\s*$', body, flags=re.M))
KO = []
for n, m in enumerate(ms, 1):
    end = ms[n].start() if n < len(ms) else len(body)
    for s, para in enumerate([x.strip() for x in re.split(r'\n\s*\n', body[m.end():end]) if x.strip()]):
        KO.append((f'{n}:{s}', para))
# 한국어 경 제목: '## 1 …' ~ '## 26 …' 차례대로
ko_su, want = [], 1
for i, (k, p) in enumerate(KO):
    if want <= 26 and re.match(rf'## {want} \S', p):
        ko_su.append((ORDER[want - 1], i, re.sub(r'^## \d+ ', '', p))); want += 1
assert len(ko_su) == 26, len(ko_su)
end_ko = next(i for i, (k, p) in enumerate(KO) if p.startswith('## 옮긴이의 말'))
start = {}
for i, o in enumerate(O):
    if o['k'] != 'fn': start.setdefault(o['mn'], i)
args = []
for j, (mn, ki, title) in enumerate(ko_su):
    ke = ko_su[j + 1][1] if j + 1 < len(ko_su) else end_ko
    if mn not in start:
        nxt = ko_su[j + 1][2] if j + 1 < len(ko_su) else '옮긴이의 말'
        args += ['--ko-skip', '^' + re.escape(KO[ki][1]) + '$|^## ' + re.escape(nxt if j + 1 == len(ko_su) else f'{j + 2} {nxt}') + '$']
        continue
    oi = start[mn]
    hs = [oi, oi + 1]          # 원서 경 제목: '26 Ariyapariyesana Sutta' + 'The Noble Search'
    pin = f"{KO[ki][0]}={'+'.join(map(str, hs))}"
    args += ['--pin', pin, '--seg', pin]
    oe = oi
    while oe < len(O) and O[oe]['mn'] == mn: oe += 1
    kn = {}
    for i in range(ki + 1, ke):
        m = re.match(r'\*\*(\d+)\*\*\s', KO[i][1])
        if m: kn.setdefault(int(m.group(1)), []).append(i)
    on = {}
    for i in range(oi, oe):
        if O[i]['k'] != 'p': continue
        n = O[i].get('sec')
        if n is None:
            m = re.match(r'(\d+)\. ', O[i]['t']); n = int(m.group(1)) if m else None
        if n is not None: on.setdefault(int(n), []).append(i)
    for n in kn:
        if len(kn[n]) == 1 and len(on.get(n, [])) == 1:
            args += ['--seg', f"{KO[kn[n][0]][0]}={on[n][0]}"]   # 단락 번호는 경계로만(쪽을 넘어 이어지는 한국어 문단도 함께 짝지어지게)
# 소제목 짝: 경마다 한국어 '## ' 소제목 ↔ 원서 소제목을 차례대로 (수가 다른 경은 손으로)
HEADS = {38: {'Setting': None},   # 한국어판에 없는 소제목
         10: {'(CONTEMPLATION OF THE BODY)': None, '(CONTEMPLATION OF MIND-OBJECTS)': None},   # 한국어판은 '몸에 대한 관찰: 1. …' 처럼 합쳐 적음
         118: {'서품': 'Introductory Section', '호흡 알아차림': 'Mindfulness of Breathing',
               '알아차림의 네 가지 토대 - 사념처의 실현': 'Fulfilment of the Four Foundations of Mindfulness',
               '일곱 깨달음의 요소(七覺支)의 실현': 'Fulfilment of the Seven Enlightenment Factors',
               '진정한 지혜와 해탈의 실현': 'Fulfilment of True Knowledge and Deliverance'}}
SKIPH = {('38', 'The Ending of the Round: The Gradual Training')}   # 아래 EXTRA 가 묶음으로 짝지음
for j, (mn, ki, title) in enumerate(ko_su):
    if mn not in start: continue
    ke = ko_su[j + 1][1] if j + 1 < len(ko_su) else end_ko
    oi = start[mn]; oe = oi
    while oe < len(O) and O[oe]['mn'] == mn: oe += 1
    kh = [i for i in range(ki + 1, ke) if KO[i][1].startswith('## ')]
    oh = [i for i in range(oi + 2, oe) if O[i]['k'] == 'h']
    if mn == 118:
        prs = [(k, next(o for o in oh if O[o]['t'] == HEADS[118][KO[k][1][3:]])) for k in kh if KO[k][1][3:] in HEADS[118]]
    else:
        oh = [o for o in oh if O[o]['t'] not in HEADS.get(mn, {})]
        if len(kh) != len(oh): raise SystemExit(f'MN {mn} 소제목 수가 다름 {len(kh)} {len(oh)}')
        prs = list(zip(kh, oh))
    for k, o in prs:
        if (str(mn), O[o]['t']) in SKIPH: continue
        args += ['--pin', f'{KO[k][0]}={o}', '--seg', f'{KO[k][0]}={o}']
# 원서가 '…as Sutta 27, §§11-18…' 처럼 줄여 적어 단락 번호가 없는 곳: 한국어 단락 ↔ 원서 소제목을 경계로
#   MN38 §31~38: 한국어판은 전문을 옮겼고 원서는 소제목 + '…as Sutta 27, §§11-18…' 한 문단 → 묶음 하나로 짝지음
EXTRA = {38: (31, 39, ['The Ending of the Round: The Gradual Training', '“Here, bhikkhus, a Tathāgata appears'])}
for mn, (n0, n1, hs) in EXTRA.items():
    j = [x for x in range(len(ko_su)) if ko_su[x][0] == mn]
    if not j or mn not in start: continue
    j = j[0]; ki = ko_su[j][1]; ke = ko_su[j + 1][1] if j + 1 < len(ko_su) else end_ko
    k0 = next(i for i in range(ki + 1, ke) if re.match(rf'\*\*{n0}\*\*\s', KO[i][1]))
    if KO[k0 - 1][1].startswith('## '): k0 -= 1   # 한국어 소제목 '순환의 끝내기: 점차적인 훈련' 부터
    k1 = next(i for i in range(ki + 1, ke) if re.match(rf'\*\*{n1}\*\*\s', KO[i][1]))
    ks = [KO[i][0] for i in range(k0, k1) if not KO[i][1].startswith('[^')]
    os_ = [next(i for i, x in enumerate(O) if x['mn'] == mn and x['t'].startswith(h)) for h in hs]
    pin = f"{'+'.join(ks)}={'+'.join(map(str, os_))}"
    args += ['--pin', pin, '--seg', f'{ks[0]}={os_[0]}', '--seg', f'{KO[k1][0]}={os_[-1] + 1}']
print('\n'.join(args))
