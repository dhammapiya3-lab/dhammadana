"""영어 원서(스캔본) 글자 인식 결과(tsv)에서 쪽마다 문단을 만든다.
워터마크(dhammadownload)·쪽 번호 줄은 뺌. 줄 사이가 크게 벌어지면 새 문단.
줄 끝 하이픈(낱말 가운데)은 붙임. 쪽을 넘어간 문단은 이어 붙임.
결과: en_paras.json = [{"pg": 인쇄 쪽(PDF 쪽), "t": 글}, ...]
"""
import csv, glob, json, re, statistics, sys

def lines_of(path):
    rows = list(csv.DictReader(open(path), delimiter='\t', quoting=csv.QUOTE_NONE))
    L = {}
    for r in rows:
        if r['level'] == '5' and (r['text'] or '').strip():
            k = (int(r['block_num']), int(r['par_num']), int(r['line_num']))
            L.setdefault(k, []).append(r)
    out = []
    for k, ws in L.items():
        txt = ' '.join(w['text'] for w in ws).strip()
        top = min(int(w['top']) for w in ws); h = max(int(w['height']) for w in ws)
        left = int(ws[0]['left'])
        out.append(dict(t=txt, top=top, h=h, left=left))
    out.sort(key=lambda x: x['top'])
    return out

def junk(t):
    if re.search(r'dhamma\s*download', t, re.I) or re.search(r'http', t): return True
    if re.fullmatch(r'[\divxlcIVXLC\s\.\-—:;,\'"|]{1,8}', t): return True  # 쪽 번호
    return False

paras = []
for f in sorted(glob.glob('tsv/p-*.tsv')):
    pg = int(re.search(r'p-(\d+)', f).group(1))
    ls = [l for l in lines_of(f) if not junk(l['t'])]
    if not ls: continue
    gaps = [b['top'] - a['top'] for a, b in zip(ls, ls[1:])]
    med = statistics.median(gaps) if gaps else 60
    cur = None
    for i, l in enumerate(ls):
        new = i == 0 or gaps[i - 1] > med * 1.55
        if new:
            if cur: paras.append(cur)
            cur = dict(pg=pg, t=l['t'])
        else:
            if re.search(r'[A-Za-z]-$', cur['t']): cur['t'] = cur['t'][:-1] + l['t']
            else: cur['t'] += ' ' + l['t']
    if cur: paras.append(cur)

# 쪽을 넘어간 문단 잇기: 앞 문단이 문장 끝 부호로 끝나지 않고 다음 쪽 첫 문단이 소문자로 시작
out = []
for p in paras:
    if out and out[-1]['pg'] != p['pg'] and not re.search(r'[.!?”"’\')]\s*$', out[-1]['t']) and len(out[-1]['t']) > 60 and p['pg'] >= 5 and not (len(p['t']) <= 60 and not re.search(r'[.!?”’]$', p['t'])):
        out[-1].setdefault('pg2', p['pg']); out[-1].setdefault('brk', len(out[-1]['t']) + 1); out[-1]['t'] += ' ' + p['t']
    else:
        out.append(p)
json.dump(out, open('en_paras.json', 'w'), ensure_ascii=False, indent=1)
print(len(out), 'paras')
