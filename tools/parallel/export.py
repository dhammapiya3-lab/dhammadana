"""원서 대조 짝 자료 → 표(TSV, 엑셀에서 열림)로 내보내기 — 다른 곳(번역 공부·용어집·앱)에 쓰기 위해
  python3 tools/parallel/export.py DL-0014 en [나갈 파일.tsv]
칸: 묶음 번호 · 한국어 쪽 · 한국어 문장 · 원서 쪽 · 원서 문장 · 뜻 비슷함(0~1)"""
import sys, json, re, os
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bk, lang = sys.argv[1], sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(REPO, 'tools/out/parallel', f'{bk}.{lang}.pairs.tsv')
D = json.load(open(os.path.join(REPO, 'content/parallel', f'{bk}.{lang}.json')))
T = json.load(open(os.path.join(REPO, 'content/texts', f'{bk}.json')))['body']
pages = re.split(r'^===\s*(.*?)\s*===\s*$', T, flags=re.M)[1:]
P = [(pages[i], pages[i + 1]) for i in range(0, len(pages), 2)]
def paras(t): return ['\n'.join(l.strip() for l in s.strip().split('\n')) for s in re.split(r'\n\s*\n', t or '') if s.strip()]
def plain(s): return re.sub(r'\*\*|==|°°|§§|\[\^[^\]]+\]|^(## |\^\^ |:: |>> |\+\+ )', '', s, flags=re.M).replace('\n', ' ').replace('\t', ' ')
def kt(k): n, s = map(int, k.split(':')); return P[n - 1], paras(P[n - 1][1])[s]
rows = ['묶음\t한국어 쪽\t한국어\t원서 쪽\t원서\t뜻 비슷함']
for gi, g in enumerate(D['groups'], 1):
    for s in g['s']:
        ko = ' '.join(plain(kt(k)[1][a:b]) for k, a, b in s['ko']); kp = kt(s['ko'][0][0])[0][0] if s['ko'] else ''
        en = ' '.join(plain(D['orig'][i]['t'][a:b]) for i, a, b in s['or']); ep = D['orig'][s['or'][0][0]]['pg'] if s['or'] else ''
        rows.append(f"{gi}\t{kp}\t{ko}\t{ep}\t{en}\t{s.get('sc', '')}")
open(out, 'w', encoding='utf-8-sig').write('\n'.join(rows) + '\n')
print(len(rows) - 1, '줄 →', out)
