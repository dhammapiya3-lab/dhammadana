# 『위빠싸나 성자 아짠 문』(DL-0040) 태국어 원서 글 뽑기 (운영자 요청, 2026-11-28)
#   원서: ประวัติท่านพระอาจารย์มั่น ภูริทัตตเถระ (ท่านอาจารย์พระมหาบัว ญาณสัมปันโน 엮음) — PDF 287쪽, 글자층이 쓸 수 없는 글리프 번호라
#   쪽 그림을 글자 인식(tesseract tha, 줄마다 psm 7 — 윗줄 성조 부호 띠를 글줄에 붙여 따로 줄로 읽히지 않게)한 결과(작업 폴더 ocrC/NNN.json(세 번 인식 다수결 + 성조 부호 바로잡기))에서 만듦.
#   python3 tools/parallel/th_dl0040.py <ocr 폴더> [고친 곳 목록 tools/parallel/dl0040_th_fix.tsv]
#   쪽 이름: 쪽 위 오른쪽 태국 숫자 — 번호 없는 쪽(표지·사진 1·3·5·133·153·246·277·282)을 빼고 차례대로 (PDF 2 = 2쪽, PDF 4 = 3쪽 … PDF 287 = 280쪽)
#   문단: 첫 줄을 들여 쓴 줄(x0 > 330)에서 새 문단, 줄은 빈칸 없이 이음(태국어 줄은 낱말 경계에서 바뀜).
#   제목: 상자 안 제목 줄(차례 항목과 같은 글) → 'h'. 상자 선·밑줄이 글자로 읽힌 줄(사전 낱말이 반이 안 되는 줄)은 뺌.
import sys, json, os, re, difflib
from pythainlp import word_tokenize
from pythainlp.corpus import thai_words
W = set(thai_words())
src = sys.argv[1]
FIX = []
fx = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), 'dl0040_th_fix.tsv')
if os.path.exists(fx):
    for l in open(fx, encoding='utf-8'):
        if l.strip() and not l.startswith('#'):
            p = l.rstrip('\n').split('\t'); FIX.append((int(p[0]), p[1], p[2]))   # PDF 쪽, 찾을 글, 바꿀 글
NOPG = {1, 3, 5, 133, 153, 246, 277, 282}
def pgname(pdf):
    return None if pdf in NOPG else pdf - sum(1 for x in NOPG if x < pdf) + 1
THAI = re.compile('[ก-๛]')
def clean(t):
    t = t.replace('ํา', 'ำ').replace('ํา', 'ำ')
    t = re.sub(r'(?<=\s)!(?=\s|$)', 'ๆ', t); t = re.sub(r'(?<=[ก-๏])\s*!(?=\s)', ' ๆ', t)
    t = re.sub(r'[|\]\[]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t
def words_ok(t):
    # 사전 낱말에 든 태국 글자의 비율 (글자 수로) — 상자 선·장식 무늬가 글자로 읽힌 줄은 낮음
    toks = [x for x in word_tokenize(t.replace(' ', ''), keep_whitespace=False) if THAI.search(x)]
    tot = sum(len(x) for x in toks)
    if not tot: return 0
    return sum(len(x) for x in toks if (x in W and len(x) > 1) or x in 'ๆฯ') / tot
def fixspace(t):
    # 고르게 맞춘 줄에서 낱말 가운데에 들어간 빈칸 빼기: 빈칸 양쪽 조각이 사전에 없고 붙이면 사전 낱말이 되면 붙임
    parts = t.split(' ')
    out = [parts[0]]
    for p in parts[1:]:
        a = out[-1]
        if a and p and THAI.match(p[0]) and p[0] not in 'ๆฯ' and THAI.search(a[-1]):
            la = word_tokenize(a, keep_whitespace=False)[-1]; fp = word_tokenize(p, keep_whitespace=False)[0]
            j = word_tokenize(la + fp, keep_whitespace=False)
            if (la not in W or fp not in W) and len(j) == 1 and j[0] in W: out[-1] = a + p; continue
        out.append(p)
    return ' '.join(out)
# 제목: 차례(PDF 2쪽)에 인쇄된 이름 그대로 — 본문 제목은 상자 안에 있어 글자 인식이 흔들리므로 자리(PDF 쪽, 줄 위쪽 y — None 이면 그 쪽의 상자 제목 줄)만 정함
HEADS = {4: (463, 'คำนำ โดย พระมหาบัว'), 6: (475, 'ประวัติ ท่านพระอาจารย์มั่น ภูริทัตตเถระ'), 7: (1674, 'เกิดสุบินนิมิต'), 9: (1369, 'เกิดสมาธินิมิต'),
         20: (2175, 'เวลาท่านพักอยู่ในถ้ำนี้ มีรู้อะไรแปลก ๆ หลายอย่าง'), 30: (594, 'พระสาวกอรหันต์มาแสดงธรรมให้ฟัง'),
         70: (633, 'ข้อวัตรประจำองค์ท่านโดยเฉพาะในมัชฌิมวัย'), 106: (1187, 'พระพุทธเจ้าและพระสาวกอรหันต์เสด็จมาอนุโมทนา'),
         134: (374, 'เทวดาประเทศเยอรมันมาขอฟังเทศน์ท่าน'), 143: (755, 'ท้าวสักกเทวราชบนสวรรค์มาเยี่ยมท่านเสมอ'),
         154: (260, 'ลูกศิษย์กับอาจารย์โต้นรก-สวรรค์กัน'), 159: (2371, 'ท่านพิจารณาเห็นถ้ำด้วยตาทิพย์'),
         167: (1597, 'พระอรหันต์มานิพพานที่ถ้ำเชียงดาว ๓ องค์'), 181: (2074, 'พระมหาเถระถามปัญหาท่านพระอาจารย์มั่น'),
         226: (1205, 'ท่านพระอาจารย์มั่นเริ่มป่วย และเริ่มลาวัฏวนเป็นครั้งสุดท้าย'), 228: ('ins1831', 'ท่านเทศน์อัศจรรย์ครั้งสุดท้าย'),
         247: (290, 'อัฐิท่านพระอาจารย์มั่นกลายเป็นพระธาตุ'), 278: (390, 'ปัญหา ม.ร.ว.คึกฤทธิ์'),
         283: (378, 'อันเนื่องมาแต่ประวัติท่านพระอาจารย์มั่น ภูริทัตตเถระ'),
         285: (354, 'ตอบปัญหาของท่านผู้ถามเกี่ยวกับพระอาจารย์มั่น ภูริทัตตเถระ')}
SKIP = {(2, 2602), (278, 589), (283, 663), (283, 709), (285, 544), (285, 474)}   # 제목 상자 안 아랫줄(신문 이름·날짜 — 상자 그림이라 읽을 수 없는 줄)
# 글자 인식이 되풀이해서 틀리는 낱말 (쪽 그림으로 확인한 꼴만, 낱말 단위로 — 다른 낱말 속 글자는 건드리지 않음)
TOKFIX = {'นัน': 'นั้น', 'ขีน': 'ขึ้น', 'ขึน': 'ขึ้น', 'ขิ้น': 'ชิ้น', 'ถำ': 'ถ้ำ', 'นี': 'นี้', 'ซั้ำ': 'ซ้ำ', 'อื่ม': 'อิ่ม', 'ลัม': 'ล้ม', 'เมือ': 'เมื่อ', 'ทีไม่': 'ที่ไม่', 'กี': 'ก็'}
STRFIX = [('อุตสำห์', 'อุตส่าห์'), ('กระหื่ม', 'กระหึ่ม'), ('อื่มพอ', 'อิ่มพอ'), ('กิเสส', 'กิเลส'), ('หัวคำ', 'หัวค่ำ'), ('*”', '”'), ('*', '”')]   # 닫는 큰따옴표를 '*' 로 읽은 곳
def tokfix(t):
    for a, b in STRFIX: t = t.replace(a, b)
    return ''.join(TOKFIX.get(w, w) for w in word_tokenize(t, keep_whitespace=True))
pages = [json.load(open(os.path.join(src, f'{i:03d}.json'))) for i in range(287)]
toc = []
paras = []
for d in pages:
    pdf = d['pdf']; pg = pgname(pdf)
    L = [l for l in d['lines'] if 250 < l['y0'] < 2990 and l['y1'] - l['y0'] >= 28]
    for l in L:
        t = clean(l['t'])
        for (fp, a, b) in FIX:
            if fp == pdf and a in t: t = t.replace(a, b)
        l['c'] = tokfix(t)
    if pdf == 2:   # 차례: 1~19 항목
        for l in L:
            m = re.match(r'(\d+)\.\s*(.+?)(?:\s+[๐-๙]+)?$', l['c'])
            if m: toc.append(re.sub(r'\s+', ' ', m.group(2)).strip())
    cur = None
    if pdf in NOPG: continue   # 표지·사진 쪽
    for l in L:
        t = l['c']
        hy, htitle = HEADS.get(pdf, (False, None))
        if htitle and isinstance(hy, int) and abs(l['y0'] - hy) < 6:
            paras.append({'pg': pg, 'pdf': pdf, 'k': 'h', 't': htitle}); cur = None; continue
        if (pdf, l['y0']) in SKIP: continue
        if not t or len(THAI.findall(t)) < 3 and not re.search(r'[0-9๐-๙]', t): continue
        if words_ok(t) < .6: continue
        t = fixspace(t)
        hy, htitle = HEADS.get(pdf, (False, None))
        if isinstance(hy, str) and hy.startswith('ins') and l['y0'] >= int(hy[3:]) and not any(p.get('_ins') == pdf for p in paras):
            paras.append({'pg': pg, 'pdf': pdf, 'k': 'h', 't': htitle, '_ins': pdf}); cur = None
        boxh = l['y1'] - l['y0'] > 85 and l['x0'] > 400
        if pdf == 2:
            paras.append({'pg': pg, 'pdf': pdf, 'k': 'toc', 't': t}); cur = None; continue
        if htitle and isinstance(hy, int) and abs(l['y0'] - hy) < 6:
            paras.append({'pg': pg, 'pdf': pdf, 'k': 'h', 't': htitle}); cur = None; continue
        if htitle and isinstance(hy, int) and hy - 130 < l['y0'] < hy + 160 and l['x0'] > 400 and l['x1'] < 1760: continue   # 제목 상자 위아래 줄(상자 선이 읽힌 것)
        if boxh and l['x1'] - l['x0'] < 1300: continue   # 상자 제목·그림 둘레에서 읽힌 조각
        center = l['x0'] > 450 and l['x1'] < 1700
        if cur is None or l['x0'] > 330 or center or (paras and paras[-1].get('_end')):
            cur = {'pg': pg, 'pdf': pdf, 'k': 'p', 't': t}; paras.append(cur)
        else:
            cur['t'] += t
        cur['_end'] = center or l['x1'] < 1700   # 짧은 줄로 끝나면 문단 끝
        if center: cur = None
    # 쪽이 넘어가도 문단은 이어짐 (다음 쪽 첫 줄을 들여 쓰지 않았으면)
for p in paras: p.pop('_end', None); p.pop('_ins', None)
out = os.path.join(os.path.dirname(__file__), '..', 'out', 'parallel', 'DL-0040.th.paras.json')
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(paras, open(out, 'w'), ensure_ascii=False, indent=0)
print('원서 문단', len(paras), '제목', sum(1 for p in paras if p['k'] == 'h'), '차례 항목', len(toc), '→', os.path.normpath(out))
