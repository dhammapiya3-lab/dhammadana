"""GRETIL 율장 HTML → 학습 자료실 본문 글.
원칙: 원문 글자는 하나도 바꾸지 않는다. 하는 일은 (1) HTML 태그를 줄바꿈/빈 글로 바꾸기, (2) &amp; 같은 HTML 글자 표기를 글자로,
(3) 쪽 표시만 찾기 좋은 모양으로 바꾸기: [page 002] → '=== Vin I 2 ===', [PTS Page 002] [\\q 2/] → '=== Vin II 2 ===', [BJT Page 4] [\\x 4/] → '[BJT 4]'.
쪽 표시 안에 섞여 들어간 원문 글자(@, '' 등)는 그대로 살린다. 검수: verify() 가 공백을 뺀 글자 줄을 원문과 한 자씩 대조한다.
"""
import re, html, json, sys
U = '/mnt/user-data/uploads/'
PTS = [('8ebc14db-vin1mapu.htm', 'I', 'Mahāvagga', '마하왁가(대품)', '1879'),
       ('4bb62f07-vin2cupu.htm', 'II', 'Cullavagga', '쭐라왁가(소품)', '1880'),
       ('b301a834-vin3s1pu.htm', 'III', 'Suttavibhaṅga, First Part', '숫따위방가 1', '1881'),
       ('4df4a353-vin4s2pu.htm', 'IV', 'Suttavibhaṅga, Second Part', '숫따위방가 2', '1882'),
       ('4bb906f3-vin5papu.htm', 'V', 'Parivāra', '빠리와라(부수)', '1883')]
BJT = [('c1361381-mahavg_u.htm', 'Mahāvaggapāḷi', '마하왁가(대품)'), ('6344500f-cullav_u.htm', 'Cullavaggapāḷi', '쭐라왁가(소품)'),
       ('0ee3bb43-paraji_u.htm', 'Pārājikapāḷi', '빠라지까'), ('ffa8d394-pacitt_u.htm', 'Pācittiyapāḷi', '빠찟띠야'),
       ('de20e0fd-pariva_u.htm', 'Parivārapāḷi', '빠리와라(부수)')]

def body(s): return s.split('<body>', 1)[1].rsplit('</body>', 1)[0]
def untag(s):
    s = re.sub(r'(?i)<br\s*/?>\r?\n?', '\n', s)
    s = re.sub(r'(?i)</?(p|tr|table|hr)[^>]*>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    return html.unescape(s)
def tidy(s):  # 공백만 정리 (글자는 그대로)
    s = re.sub(r'[ \t]+\n', '\n', s); return re.sub(r'\n{3,}', '\n\n', s).strip()

R_PTS_PAGE = r'\[page (\d+)\]'
R_PTS_REF = r'\[PTS\s+Page\s*(\d+)([^\]\[]*?)(?:\[\\q[^\]]*\]([^\]\[]*))?\]\s*(?:\[\\q\s*\d+\s*/\])?'
R_BJT_REF = r'\[BJT\s+Page\s*(\d+)([^\]\[]*?)\]?\s*\[\\x\s*\d+\s*/\]'
R_HEAD = r'\[(?:PTS|BJT)\s+Vol[^\]]*\]\s*\[\\z[^\]]*\]\s*\[\\[fw][^\]]*\]'

def conv_pts(f, vol):
    t = untag(body(open(U + f, encoding='utf-8').read()))
    return tidy(re.sub(R_PTS_PAGE, lambda m: f'\n=== Vin {vol} {int(m.group(1))} ===\n', t))
def conv_bjt(f):
    t = untag(body(open(U + f, encoding='utf-8').read()))
    vol = re.search(r'\[\\f ([IVX]+) /\]', t).group(1)
    t = re.sub(R_HEAD, lambda m: '', t)
    t = re.sub(R_PTS_REF, lambda m: f'\n=== Vin {vol} {int(m.group(1))} ===\n' + (m.group(2) or '').strip() + ((m.group(3) or '').strip()), t)
    t = re.sub(R_BJT_REF, lambda m: f'⟦BJT {int(m.group(1))}⟧' + (m.group(2) or '').strip(), t)
    return tidy(t), vol

def canon_src(f, bjt):
    t = untag(body(open(U + f, encoding='utf-8').read()))
    if bjt:
        t = re.sub(R_HEAD, '', t)
        t = re.sub(R_PTS_REF, lambda m: (m.group(2) or '') + (m.group(3) or ''), t)
        t = re.sub(R_BJT_REF, lambda m: (m.group(2) or ''), t)
    else:
        t = re.sub(R_PTS_PAGE, '', t)
    return re.sub(r'\s+', '', t)
def canon_out(t):
    t = re.sub(r'=== Vin [IVX]+ \d+ ===', '', t); t = re.sub(r'⟦BJT \d+⟧', '', t)
    return re.sub(r'\s+', '', t)

def verify(f, out, bjt):
    a, b = canon_src(f, bjt), canon_out(out)
    if a == b: return 'OK'
    i = next(i for i in range(min(len(a), len(b))) if a[i] != b[i]) if a[:min(len(a), len(b))] != b[:min(len(a), len(b))] else min(len(a), len(b))
    return f'다름 @{i}: 원문 …{a[i-30:i+30]}… / 결과 …{b[i-30:i+30]}…'

if __name__ == '__main__':
    out = []
    for f, vol, name, ko, yr in PTS:
        t = conv_pts(f, vol)
        out.append(dict(id=f'PTS-Vin{vol}', src=f, vol=vol, name=name, ko=ko, year=yr, ed='pts', text=t))
        print(out[-1]['id'], len(t), len(re.findall(r'^=== ', t, re.M)), verify(f, t, False))
    for f, name, ko in BJT:
        t, vol = conv_bjt(f)
        out.append(dict(id='BJT-' + name.replace('pāḷi', ''), src=f, vol=vol, name=name, ko=ko, ed='bjt', text=t))
        left = re.findall(r'\[(?:PTS|BJT)\s+(?:Page|Vol)|\[\\[qxzfw]', t)
        print(out[-1]['id'], 'Vin', vol, len(t), len(re.findall(r'^=== ', t, re.M)), 'leftover', len(left), verify(f, t, True))
    json.dump(out, open('vin.json', 'w'), ensure_ascii=False)
