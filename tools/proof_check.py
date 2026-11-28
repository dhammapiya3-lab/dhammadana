#!/usr/bin/env python3
"""교정 정밀 검사 묶음 (운영자 요청, 2026-11-28 — '정밀한 교정을 위해 더 고려할 것')

결과는 모두 '확인할 곳'이다. 바로 고치지 않고 목록으로 보여 드린 뒤 정한 것만 고친다.

① 조사와 받침 — 앞말 받침과 맞지 않는 조사(데와을·브라흐마이·상가과 …). 음역·이름을 바꾼 뒤 꼭 돌림.
② 한자 소리 — '삼계(三界)'처럼 한글 바로 뒤(또는 괄호 안)의 한자 소리가 앞 한글과 다른 곳.
   두음법칙·여러 소리 글자(樂 說 不 …)는 같은 것으로 봄. 뜻풀이로 붙인 한자(수닷시(善現))도 나오므로 가름.
③ 로마자 — 빠알리 사전(DPD 낱말·변화형, public/data/pali-words.txt)과 모든 책의 로마자에 없는 꼴,
   그리고 점·막대를 뺀 꼴은 같은데 부호가 다른 꼴이 모든 책에서 훨씬 많이 쓰이는 낱말(Puraṇa / Purāṇa).
④ 같은 문장 되풀이 — 가까운 곳(같은 장)에 같거나 거의 같은 문장이 다시 실린 곳(독송·게송 줄은 뺌).
⑤ 문장 부호 — 겹친 부호(?. !. ..), 부호 앞 빈칸, 쉼표 뒤 빈칸 없음, 문단 안 괄호·따옴표 짝.
⑥ 문체 섞임 — 한 장 안에서 '-습니다'와 '-다'가 섞인 곳의 적은 쪽 문장(따옴표 안 글은 뺌). 여쭐 곳.

쓰는 법: python3 tools/proof_check.py <ID> [--out 결과.tsv]
"""
import json, re, sys, glob, collections, unicodedata, difflib, os
from kiwipiepy import Kiwi
import hanja

ID = sys.argv[1]
out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else f'tools/out/proof/{ID}.tsv'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(f'{ROOT}/content/texts/{ID}.json', encoding='utf-8'))
body = d['body']
MARK = re.compile(r'\*\*|°°|@@|__|==|§§|\{\{|\}\}|\[\^[^\]]*\]:?')
rows = []
def add(kind, pg, now, sug, why, ctx):
    rows.append((kind, pg, now, sug, why, ctx.replace('\t', ' ')[:160]))

# 본문을 (쪽, 장 번호, 글 종류, 글) 줄로
lines = []; page = ''; chap = 0
for raw in body.split('\n'):
    m = re.match(r'^=== (.*) ===$', raw)
    if m: page = m.group(1); continue
    if raw.startswith('## ') or raw.startswith('^^ '): chap += raw.startswith('^^ ')
    if raw.startswith('![') or raw.startswith('%%') or raw.startswith('|') or raw.strip() == '~': continue
    kind = 'fn' if raw.startswith('[^') else ('verse' if re.match(r'^(\+\+|::|>>)', raw) else ('head' if re.match(r'^(## |\^\^ )', raw) else 'p'))
    t = MARK.sub('', raw)
    t = re.sub(r'^(\^\^|::|>>|\+\+|\|\||## )\s*', '', t).strip()
    if t: lines.append((page, chap, kind, t))

def jong(ch):
    o = ord(ch) - 0xAC00
    return None if not 0 <= o < 11172 else o % 28   # 0 = 받침 없음, 8 = ㄹ

# ① 조사와 받침
kiwi = Kiwi()
PAIR = {'을': 1, '를': 0, '은': 1, '는': 0, '이': 1, '가': 0, '과': 1, '와': 0, '으로': 1, '로': 0, '이나': 1, '나': 0, '이랑': 1, '랑': 0}
JTAG = re.compile(r'^(JKS|JKO|JX|JKB|JC|JKC)$')
def before_char(t, i):
    """조사 앞 글자: 닫는 괄호면 괄호 앞 글자."""
    j = i - 1
    if j >= 0 and t[j] in ')）':
        depth = 0
        while j >= 0:
            if t[j] in ')）': depth += 1
            elif t[j] in '(（':
                depth -= 1
                if depth == 0: break
            j -= 1
        j -= 1
    while j >= 0 and t[j] in '’”」』':
        j -= 1
    return t[j] if j >= 0 else ''
for pg, ch, kind, t in lines:
    if kind == 'verse': continue
    for m in re.finditer(r'(?<=[가-힣)）’”」』])(으로|이나|이랑|을|를|은|는|이|가|과|와|로|나|랑)(?=[\s,.!?:;”’」』)]|$)', t):
        jo = m.group(1); c = before_char(t, m.start())
        b = jong(c) if c else None
        if b is None: continue
        need = PAIR[jo]   # 1 = 받침 있을 때 쓰는 꼴
        has = 1 if b else 0
        if jo in ('으로', '로') and b == 8: has = 0   # ㄹ 받침 + 로
        if has == need: continue
        # 낱말 안 글자일 수 있음 — kiwi 로 조사인지 확인
        s0 = max(0, m.start() - 12); seg = t[s0:m.end() + 2]
        toks = kiwi.tokenize(seg)
        pos = m.start() - s0
        if not any(tk.start == pos and JTAG.match(tk.tag) for tk in toks): continue
        w0 = t[max(0, m.start() - 8):m.end()]
        add('① 조사·받침', pg, w0, '', f"'{c}' 받침 {'있음' if b else '없음'} → '{jo}' 대신 짝 꼴", t[max(0, m.start() - 40):m.end() + 40])

# ② 한자 소리
ALT = {'樂': '락악요낙', '說': '설세열', '不': '불부', '識': '식지', '度': '도탁', '復': '복부', '惡': '악오', '行': '행항',
       '切': '절체', '殺': '살쇄', '易': '역이', '更': '경갱', '數': '수삭', '率': '율솔률', '參': '참삼', '北': '북배',
       '便': '편변', '車': '차거', '宅': '택댁', '降': '강항', '省': '성생', '洞': '동통', '若': '약야', '於': '어오',
       '契': '계결', '見': '견현', '布': '포보', '提': '제리시', '般': '반발', '刹': '찰', '諦': '제체', '那': '나', '陀': '타',
       '沙': '사', '頗': '파', '茶': '다차', '金': '금김', '龜': '귀구균', '辰': '진신', '索': '색삭', '拓': '척탁',
       '句': '구귀', '辟': '벽피', '僧': '승', '般': '반발', '暴': '폭포', '葉': '엽섭', '畵': '화획', '亡': '망무', '否': '부비', '比': '비', '丹': '단란', '說': '설세열'}
DUEUM = {'라': '나', '래': '내', '로': '노', '뢰': '뇌', '루': '누', '르': '느', '랑': '낭', '락': '낙', '란': '난', '람': '남',
         '랍': '납', '량': '양', '려': '여', '력': '역', '련': '연', '렬': '열', '렴': '염', '렵': '엽', '령': '영', '례': '예',
         '료': '요', '룡': '용', '류': '유', '륙': '육', '륜': '윤', '률': '율', '륭': '융', '리': '이', '린': '인', '림': '임',
         '립': '입', '녀': '여', '뇨': '요', '뉴': '유', '니': '이', '년': '연', '념': '염', '녕': '영', '닉': '익', '록': '녹',
         '론': '논', '롱': '농', '뢰': '뇌', '룡': '용', '름': '늠', '릉': '능', '렬': '열', '륵': '늑'}
def readings(c):
    c = unicodedata.normalize('NFKC', c)
    r = hanja.translate(c, 'substitution')
    s = set(ALT.get(c, '')) | ({r} if re.match('[가-힣]', r) else set())
    for x in list(s):
        if x in DUEUM: s.add(DUEUM[x])
        for k, v in DUEUM.items():
            if v == x: s.add(k)
    return s
HANJA_GLOSS = [0]
HAN = '[㐀-鿿豈-﫿]'
for pg, ch, kind, t in lines:
    for m in re.finditer(rf'([가-힣]+)\s?\(({HAN}+)(?=[,，)\s·/])', t):
        ko, hz = m.group(1), m.group(2)
        if re.match(rf'\s*[·,，/]\s*{HAN}', t[m.end():]): continue   # 欲界· 色界 … 목록
        k = ko[-len(hz):]
        if len(k) < len(hz): continue
        if all(kc in readings(hc) for kc, hc in zip(k, hz)): continue
        # 한자 앞부분만 맞는 경우(낱말 끝 조사 등) 빼고, 한 글자라도 소리가 같은 위치가 없으면 뜻풀이로 봄
        diff = [(kc, hc) for kc, hc in zip(k, hz) if kc not in readings(hc)]
        if len(hz) < 2 or len(diff) != 1: HANJA_GLOSS[0] += 1; continue   # 뜻풀이로 붙인 한자 — 세기만
        kc, hc = diff[0]; rs = readings(hc)
        def jamo(x): o = ord(x) - 0xAC00; return (o // 588, (o % 588) // 28, o % 28)
        if not any(jamo(kc)[0] == jamo(r)[0] or jamo(kc)[1:] == jamo(r)[1:] for r in rs if '가' <= r <= '힣'): HANJA_GLOSS[0] += 1; continue
        why = f"'{kc}' 자리 한자 {hc} 의 소리는 {'·'.join(sorted(r for r in rs if '가' <= r <= '힣'))} — 오자일 수 있음"
        add('② 한자 소리', pg, f'{ko}({hz})', hanja.translate(unicodedata.normalize('NFKC', hz), 'substitution'), why, t[max(0, m.start() - 30):m.end() + 30])

# ③ 로마자
def strip(w):
    w = unicodedata.normalize('NFD', w.lower())
    w = ''.join(c for c in w if unicodedata.category(c) != 'Mn')
    return w.replace('ṁ', 'm')
DIA = re.compile(r'[āīūṭḍṇñṅṃṁḷĀĪŪṬḌṆÑṄṂṀḶ]')
pali = set(open(f'{ROOT}/public/data/pali-words.txt', encoding='utf-8').read().split())
allforms = collections.Counter(); bookof = collections.defaultdict(set)
for f in glob.glob(f'{ROOT}/content/texts/*.json'):
    b = json.load(open(f, encoding='utf-8')).get('body', '')
    for w in re.findall(r"[A-Za-zāīūṭḍṇñṅṃṁḷĀĪŪṬḌṆÑṄṂṀḶ]+", MARK.sub('', b)):
        wl = unicodedata.normalize('NFC', w.lower()).replace('ṁ', 'ṃ')
        allforms[wl] += 1; bookof[wl].add(os.path.basename(f))
bystrip = collections.defaultdict(collections.Counter)
for w, n in allforms.items(): bystrip[strip(w)][w] += n
seen = set()
for pg, ch, kind, t in lines:
    for m in re.finditer(r"[A-Za-zāīūṭḍṇñṅṃṁḷĀĪŪṬḌṆÑṄṂṀḶ]+", t):
        w = m.group(); wl = unicodedata.normalize('NFC', w.lower()).replace('ṁ', 'ṃ')
        if len(w) < 4 or wl in seen: continue
        st = strip(w)
        ctx = t[max(0, m.start() - 30):m.end() + 30]
        if re.search(r'https?://\S*$|\S+@\S*$|www\.\S*$', t[:m.start()]): continue
        forms = bystrip[st]; best, bn = forms.most_common(1)[0]
        if best != wl and bn >= 5 and forms[wl] * 5 <= bn and DIA.search(best + wl):
            seen.add(wl); add('③ 로마자 부호', pg, w, best, f'모든 책에서 이 꼴 {forms[wl]}번 · {best} {bn}번 — 둘 다 맞는 낱말일 수 있음(vāta 바람 / vata 맹세)', ctx); continue
        if not DIA.search(w): continue          # 부호 없는 낱말은 영어일 수 있어 뺌
        if st in pali or len(bookof[wl]) >= 2: continue
        # 겹낱말: 사전 낱말 둘로 나뉘면 뺌
        if any(st[:i] in pali and st[i:] in pali for i in range(3, len(st) - 2)): continue
        seen.add(wl); add('③ 로마자 사전에 없음', pg, w, '', f'사전·다른 책에 없는 꼴 (이 책 {forms[wl]}번)', ctx)

# ④ 같은 문장 되풀이
SENT = re.compile(r'[^.?!。]+[.?!。]')
sents = []
for idx, (pg, ch, kind, t) in enumerate(lines):
    if kind in ('verse', 'head'): continue
    for s in SENT.findall(t):
        s = s.strip()
        if len(re.sub(r'\W', '', s)) >= 25: sents.append((pg, ch, s, re.sub(r'[\s\W]', '', s)))
SCNT = collections.Counter(x[3] for x in sents)
for i, (pg, ch, s, k) in enumerate(sents):
    if SCNT[k] >= 3: continue   # 책에서 세 번 넘게 나오는 문장은 되풀이 문구(경전 정형구)
    for j in range(i + 1, min(len(sents), i + 3)):   # 바로 뒤 두 문장 안 (경전의 되풀이 문구는 멀리 떨어져 나옴)
        pg2, ch2, s2, k2 = sents[j]
        if ch2 != ch: break
        if k == k2 or (abs(len(k) - len(k2)) < 8 and difflib.SequenceMatcher(None, k, k2).ratio() > 0.95):
            add('④ 같은 문장 되풀이', f'{pg} / {pg2}', s[:60], '', '같은 장에 거의 같은 문장이 다시 있음 — 인쇄본 확인', s2)
            break

# ⑤ 문장 부호
PUNCT = [(r'[?!]\.(?!\.)', '물음표·느낌표 뒤 마침표'), (r'(?<!\.)\.\.(?!\.)', '마침표 두 개'), (r'[,，]{2}', '쉼표 두 개'),
         (r'[가-힣A-Za-z)”’] +[,.?!;](?![.\d])', '부호 앞 빈칸'), (r'[가-힣][,，][가-힣]', '쉼표 뒤 빈칸 없음'),
         (r'[가-힣][.?!][가-힣]', '마침표 뒤 빈칸 없음')]
for pg, ch, kind, t in lines:
    for rx, why in PUNCT:
        for m in re.finditer(rx, t):
            add('⑤ 문장 부호', pg, t[max(0, m.start() - 6):m.end() + 4], '', why, t[max(0, m.start() - 40):m.end() + 30])
# 마침표 빠진 문장 끝 — '…되었다 그들의'처럼 문장을 끝내는 어미(EF) '-다' 뒤에 부호 없이 다음 말이 오는 곳
for pg, ch, kind, t in lines:
    if kind not in ('p', 'fn'): continue
    for m in re.finditer(r'(?<=[가-힣])다 (?=[가-힣])', t):
        nxt = t[m.end():m.end() + 6]
        if re.match(r'(하|한|할|했|싶|라고|고 |는 |라는|가|온|와|오|또)', nxt): continue
        if re.match(r'[가-힣]*다(\s|$)', t[m.end():m.end() + 8]): continue   # 왔다 갔다·기뻐했다 슬퍼했다
        if re.search(r'[가-힣]다 [가-힣]*$', t[max(0, m.start() - 8):m.start()]): continue
        s0 = max(0, m.start() - 15); toks = kiwi.tokenize(t[s0:m.end() + 8])
        hit = False
        for i_, tk in enumerate(toks):
            if tk.start + s0 == m.start() and tk.form == '다' and (tk.tag == 'EF' or (tk.tag == 'EC' and i_ and toks[i_ - 1].tag in ('EP', 'VCP'))): hit = True
        if hit:
            add('⑤ 마침표 빠짐', pg, t[max(0, m.start() - 15):m.end() + 10], '', "문장을 끝내는 '-다' 뒤에 부호가 없음", t[max(0, m.start() - 50):m.end() + 40])
# 쌍점 앞 빈칸은 책마다 꼴이 다름 — 적게 쓴 꼴만
c1 = [(pg, t, m) for pg, ch, k, t in lines for m in re.finditer(r'[가-힣A-Za-z)] :(?=\s)', t)]
c2 = [(pg, t, m) for pg, ch, k, t in lines for m in re.finditer(r'[가-힣A-Za-z)]:(?=\s)', t)]
if c1 and c2:
    few, many = (c1, c2) if len(c1) < len(c2) else (c2, c1)
    if len(few) * 3 <= len(many):
        for pg, t, m in few:
            add('⑤ 쌍점 꼴', pg, t[max(0, m.start() - 6):m.end() + 4], '', f"책 안에서 다른 꼴('{'X:' if few is c1 else 'X :'}') {len(many)}곳 · 이 꼴 {len(few)}곳", t[max(0, m.start() - 40):m.end() + 30])
# 괄호 짝은 문단마다, 큰따옴표 짝은 문단을 넘어 (말이 여러 문단에 걸치면 다음 문단 첫머리에 “ 를 다시 여는 꼴도 있음)
PAIRS = [('(', ')'), ('「', '」'), ('『', '』'), ('[', ']'), ('《', '》'), ('〈', '〉')]
open_q = None
for pg, ch, kind, t in lines:
    tp = re.sub(r'(^|[\s,·]|주|[①-⑳])(\d{1,3}|[가나다라마바사아자차카타파하]|[a-zA-Z])\)(?=\s|[가-힣①-⑳]|$)', r'\1', t)   # '1)'·'가)'·'주3)' 같은 번호
    for a_, b_ in PAIRS:
        if tp.count(a_) != tp.count(b_):
            st = []; bad = None
            for i, c in enumerate(tp):
                if c == a_: st.append(i)
                elif c == b_:
                    if st: st.pop()
                    else: bad = i; break
            if bad is None and st: bad = st[0]
            bad = bad or 0
            add('⑤ 괄호 짝', pg, tp[max(0, bad - 25):bad + 15], '', f"문단 안에서 '{a_}' {tp.count(a_)} · '{b_}' {tp.count(b_)} — 짝 없는 곳", tp[max(0, bad - 60):bad + 60])
    if kind == 'fn': continue
    for m in re.finditer('[“”]', t):
        if m.group() == '“':
            if open_q and open_q[2] is t and not t.startswith('“'):
                add('⑤ 큰따옴표 짝', open_q[0], t[max(0, m.start() - 20):m.start() + 10], '', '닫기 전에 다시 엶', t[max(0, m.start() - 60):m.start() + 40])
            open_q = (pg, m.start(), t)
        else:
            if not open_q:
                add('⑤ 큰따옴표 짝', pg, t[max(0, m.start() - 20):m.start() + 4], '', '열지 않았는데 닫음', t[max(0, m.start() - 60):m.start() + 20])
            open_q = None
    if open_q and open_q[2] is t: pass
    elif open_q and not t.startswith('“'):
        pass   # 앞 문단에서 연 말이 이어짐 — 이 책은 문단마다 “ 를 다시 열지 않음
    if kind == 'head' and open_q:
        add('⑤ 큰따옴표 짝', open_q[0], open_q[2][open_q[1]:open_q[1] + 30], '', '소제목 앞까지 닫지 않음', open_q[2][:160]); open_q = None

# ⑥ 문체 섞임 — 한 문단(따옴표 밖) 안에서 '-습니다'와 '-다'가 섞인 곳
def noquote(t): return re.sub(r'“[^”]*”|‘[^’]*’|「[^」]*」', '', t)
def style(s):
    s = s.rstrip(' ”’)')
    if re.search(r'[니]다[.!]$', s) and len(s) >= 3 and jong(s[-4] if s.endswith(('.', '!')) else s[-3]) == 17: return 'hab'
    if re.search(r'(니까\?|세요[.!]|시오[.!]|까요\?|어요[.!]|아요[.!]|지요[.!]|죠[.!?]|에요[.!]|예요[.!])$', s): return 'hab'
    if re.search(r'다[.!]$|라[.!]$|냐\?$|가\?$|까\?$|는가\?$', s): return 'han'
    return None
for pg, ch, kind, t in lines:
    if kind != 'p' or t.startswith(('“', '‘')) or re.match(r'^[^“]{0,12}:\s*“', t): continue
    ss = [(style(x.strip()), x.strip()) for x in SENT.findall(noquote(t))]
    ss = [x for x in ss if x[0]]
    c = collections.Counter(x[0] for x in ss)
    if len(c) == 2 and len(ss) >= 3:
        minor = min(c, key=c.get)
        if c[minor] * 2 < len(ss):
            for st, x in ss:
                if st == minor:
                    add('⑥ 문체 섞임', pg, x[-30:], '', f"이 문단은 {'-다' if minor=='hab' else '-습니다'} {c[[k for k in c if k!=minor][0]]}문장 · 이 문장만 {'-습니다' if minor=='hab' else '-다'} — 여쭐 곳", t[:200])

os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w', encoding='utf-8') as f:
    f.write('묶음\t쪽\t지금 글\t제안\t근거\t앞뒤 글\n')
    for r in rows: f.write('\t'.join(map(str, r)) + '\n')
print(out); print(collections.Counter(r[0] for r in rows)); print('뜻풀이로 붙인 한자(세기만):', HANJA_GLOSS[0])
