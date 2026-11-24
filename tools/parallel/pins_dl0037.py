"""DL-0037『사아리뿟따 이야기』 원서 대조 손 짝 만들기 — run_dl0037.sh 가 부름 (한 줄에 인자 하나).

한국어판(고요한소리 법륜·열넷)은 원서(BPS Wheel 90/92, 1987 → BPS 온라인판 2008)와 짜임이 다름 — 장이 '인간 사아리뿟따'
안에서 상수제자·도움을 주는 이·성냄이 없는 이·친구와 친척들·명상수행자 차례로 다시 묶였고, 원서 여러 곳의 글이 새 차례로
옮겨졌으며, 원서에 없는 글(숙세의 서원·과거생 이야기, 상수제자 첫머리)이 더해짐. 그래서
 ① 원서 문단을 한국어판 차례로 다시 늘어놓고(--move — 옮긴 묶음에는 '원서와 순서가 다릅니다' 메모가 붙음)
 ② 장·소제목·경 항목·본생담 항목마다 --pin·--seg 로 경계를 정함.
원서 문단 번호는 tools/parallel/en_dl0037.py 가 만든 tools/out/parallel/DL-0037.en.paras.json 기준."""
import os, re, json
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = json.load(open(os.path.join(REPO, 'content/texts/DL-0037.json')))
O = json.load(open(os.path.join(REPO, 'tools/out/parallel/DL-0037.en.paras.json')))
body = T['body'].replace('\r\n', '\n')
ms = list(re.finditer(r'^===\s*(.*?)\s*===\s*$', body, flags=re.M))
KO = []
for n, m in enumerate(ms, 1):
    end = ms[n].start() if n < len(ms) else len(body)
    for s, para in enumerate([x.strip() for x in re.split(r'\n\s*\n', body[m.end():end]) if x.strip()]):
        KO.append((f'{n}:{s}', para))


def k(rx, nth=1, after=0):
    """한국어 문단 열쇠 — 글 첫머리(정규식)로 찾음, after 번째 문단 뒤에서"""
    L = [i for i, (_, p) in enumerate(KO) if re.match(rx, p)]
    if len(L) < nth: raise SystemExit('한국어 문단을 찾지 못함: ' + rx)
    return L[nth - 1] + after


def kk(i): return KO[i][0]


def e(rx):
    """원서 문단 번호 — 글 첫머리로 찾음(확인용)"""
    L = [i for i, p in enumerate(O) if p['k'] != 'fn' and re.match(rx, p['t'])]
    if not L: raise SystemExit('원서 문단을 찾지 못함: ' + rx)
    return L[0]


# ---------- ① 한국어판 차례로 다시 늘어놓은 원서 문단 (블록 = (첫 번호, 끝 번호)) ----------
DESIRED = [(0, 66), (72, 73),
           (176, 177), (173, 175), (112, 112), (111, 111), (113, 113),      # 상수제자: 증지부 2:12 → 진리의 분별 경 → 중부 주석서 → 가르치는 인내
           (215, 221), (213, 214), (80, 81),                               # 짜뚜마 경 → 계율 제정 간청 → 데와닷따·깃타기리
           (100, 107), (109, 109), (209, 212), (110, 110), (108, 108), (114, 115),   # 도움을 주는 이
           (192, 208), (67, 71), (222, 232),                               # 성냄이 없는 이 (앗사지·라다 장로에 대한 감사는 이 장으로)
           (74, 79), (82, 99), (180, 191),                                 # 친구와 친척들
           (116, 116), (124, 124), (117, 123), (125, 172), (178, 179),     # 명상수행자 → 법륜을 굴리는 이
           (233, len(O) - 1)]
KEEP = {(0, 66), (72, 73), (74, 79), (82, 99), (116, 116), (117, 123), (125, 172), (178, 179), (233, len(O) - 1)}   # 원서 차례 그대로 둔 블록
cover = sorted(i for a, b in DESIRED for i in range(a, b + 1))
assert cover == list(range(len(O))), '빠지거나 겹친 원서 문단'
args = []
for j in range(len(DESIRED) - 2, -1, -1):   # 뒤에서부터: 옮길 블록을 바로 다음 블록 앞으로
    a, b = DESIRED[j]
    if (a, b) in KEEP: continue
    args += ['--move', f'{a}-{b}>{DESIRED[j + 1][0]}']


def pin(ko, en):
    s = f"{'+'.join(kk(i) for i in ko)}={'+'.join(map(str, en))}"
    return ['--pin', s, '--seg', s]


def seg(ko, en): return ['--seg', f'{kk(ko)}={en}']


def none(*ko): return ['--pin', '+'.join(kk(i) for i in ko) + '=']


# ---------- ② 경계 ----------
i = k(r'>> \*\*The Life of')
args += pin(range(i, i + 6), [0, 1, 2, 3, 4, 5])                    # 원서 속표지 ↔ 원서 판권 면 위쪽
args += ['--pin', '=6+7+8']                                         # 원서 판권 글(1987·2008·출처)은 한국어판에 없음
args += none(*range(k(r'!\[#법륜\]'), k(r'!\[#법륜\]') + 4))          # 한국어 속표지
args += none(*[x for x in range(k(r'\* 이 책에 나오는 경'), k(r'\* 주는 원주') + 1)])   # 일러두기
args += pin([k(r'## 들어가는 말')], [e(r'Prologue')])
args += pin([k(r'## Ⅰ\. 법을 찾아서')], [15, 16]) + none(k(r'## 초년기'))
args += pin([k(r'## Ⅱ\. 인간')], [72, 73]) + none(k(r'## 상수제자'))
args += seg(k(r'부처님께서는 승가의 여러 비구들에게 두 상수제자'), 176)
args += seg(k(r'부처님은 〈진리의 분별 경'), 173)
args += seg(k(r'이 구절을 《중부》의 주석서'), 112)
args += seg(k(r'세존께서는 두 상수제자 사아리뿟따와 목갈라아나로 하여금'), 215)
args += seg(k(r'부처님께 승가 계율을 정해'), 213)
args += seg(k(r'부처님께서는 긴요한 상황이 생기면'), 80)
args += pin([k(r'## 도움을 주는 이')], [100])
args += seg(k(r'또 다른 예로 사아리뿟따가 부처님의 대시주자'), 109)
args += seg(k(r'한번은 부처님께서 가르침이 충분하지 않았다고'), 209)
args += seg(k(r'찬나 장로가 앓아누워'), 110)
args += seg(k(r'아나아타삔디까가 세상을 떠나게'), 108)
args += seg(k(r'법으로 도움을 베풀 때에도'), 114)
args += pin([k(r'## 성냄이 없는 이')], [192])
args += seg(k(r'그러니 부처님의 가르침을 접하게 해주었던 앗사지'), 67)
args += seg(k(r'사아리뿟따 존자의 참을성과 겸손함은 그가 억울한'), 222)
args += pin([k(r'## 친구와 친척들')], [74])
args += seg(k(r'앞에서 이미 보았듯이 사아리뿟따는'), 181)
args += pin([k(r'## 명상수행자')], [116])
args += pin([k(r'## Ⅲ\. 법륜을')], [133])
args += none(k(r'## 여러 가지 경$'), k(r'## 여러 가지 주석서'), k(r'## 아비담마'))
args += pin([k(r'## Ⅳ\. 피안을')], [233, 234]) + pin([k(r'## 마지막 빚을')], [235])
args += pin([k(r'## 쭌다 경')], [e(r'Cunda Sutta')]) + pin([k(r'## 욱까쩰라 경')], [e(r'Ukkacela Sutta')])
args += pin([k(r'## Ⅴ\. 사아리뿟따와')], [344, 345])
args += pin([k(r'## 중부')], [347])
for rx, en in [(r'## 3경 ', r'No\. 3:'), (r'## 5경 ', r'No\. 5:'), (r'## 9경 ', r'No\. 9:'), (r'## 28경 〈대', r'No\. 28: The Greater'),
               (r'## 43경 ', r'No 43:'), (r'## 69경 ', r'No\. 69:'), (r'## 97경 ', r'No\. 97:'), (r'## 114경 ', r'No\. 114:'),
               (r'## 143경 ', r'No\. 143:'), (r'## 28경 〈신심', r'No\. 28: Faith')]:
    args += pin([k(rx)], [e(en)])
args += pin([k(r'## 장부')], [e(r'Digha Nikaya')])
args += seg(k(r'## 33경 '), e(r'No\. 33: Doctrinal')) + none(k(r'## 34경 '), k(r'## 34경 ', after=1))
args += pin([k(r'## 증지부')], [e(r'Anguttara Nikaya')])
# 증지부 항목: 한국어 '## N법집: M경' 제목 다음 문단 ↔ 원서 'N:M: …' 한 문단 (제목은 짝 없음)
AN = [(r'## 2법집', r'2:37'), (r'## 3법집: 21경', r'3:21'), (r'## 4법집: 79경', r'4:79'), (r'## 4법집: 158경', r'4:156'),
      (r'## 4법집: 167', r'4:167f'), (r'## 4법집: 172경', r'4:171'), (r'## 4법집: 173경', r'4:172'), (r'## 4법집: 174경', r'4:173'), (r'## 4법집: 175경', r'4:175'),
      (r'## 4법집: 179경', r'4: 179'), (r'## 5법집: 165경', r'5:165'), (r'## 5법집: 167경', r'5:167'), (r'## 6법집: 14', r'6:14'),
      (r'## 6법집: 41경', r'6:41'), (r'## 7법집: 66경', r'7:66'), (r'## 9법집: 6경', r'9: 6'), (r'## 9법집: 11경', r'9: 11'),
      (r'## 9법집: 13경', r'9: 13'), (r'## 9법집: 14경', r'9:14'), (r'## 9법집: 26경', r'9:26'), (r'## 9법집: 34경', r'9:34'),
      (r'## 10법집: 7경', r'10:7'), (r'## 10법집: 65경', r'10:65'), (r'## 10법집: 66경', r'10:66'), (r'## 10법집: 67', r'10: 67'),
      (r'## 10법집: 90경', r'10:90')]
for rx, en in AN:
    i = k(rx); args += none(i) + seg(i + 1, e(re.escape(en)))
# 한국어판 4법집 172·173·174경 = 원서 4:171·172·173 (경 번호 세는 법이 다름)
args += pin([k(r'## 상응부')], [e(r'Samyutta Nikaya')])
for rx, en in [(r'## 제12 ', r'Nidana Samyutta'), (r'## 제22 ', r'Khandha Samyutta'), (r'## 제28 ', r'Sariputta Samyutta'),
               (r'## 제35 ', r'Salayatana Samyutta'), (r'## 제38 ', r'Jambukhadaka Samyutta'), (r'## 제48 ', r'Indriya Samyutta'),
               (r'## 제55 ', r'Sotapatti Samyutta')]:
    args += pin([k(rx)], [e(en)])
args += pin([k(r'## Ⅵ\. ')], [428, 429])
# 본생경 항목: 한국어 '## N. 〈… 전생담〉(번호)' 제목 + 다음 문단 ↔ 원서 'Xxx Jataka (번호): …' 한 문단 (제목은 짝 없음)
for i, (key, p) in enumerate(KO):
    m = re.match(r'## \d+\. 〈.*?〉\((\d+)\)', p)
    if not m: continue
    no = m.group(1)
    oi = next(j for j, o in enumerate(O) if j > e(r'The following are summaries of Jatakas') and o['k'] == 'p' and re.match(rf'[^(:]*\({no}\)', o['t']))
    args += none(i) + seg(i + 1, oi)
args += pin([k(r'## 덧붙이는 말')], [e(r'Appendix')]) + pin([k(r'## 사아리뿟따와 마하 목갈라아나의 사리')], [e(r'A Note on the Relics')])
print('\n'.join(args))
