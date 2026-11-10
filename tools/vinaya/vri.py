"""VRI(Vipassana Research Institute) 6차 결집본(Chaṭṭha Saṅgāyana, CSCD) 빠알리 율장 XML → 학습 자료실 본문 글.
원본: github.com/VipassanaTech/tipitaka-xml  romn/vin01m.mul.xml … vin02m4.mul.xml (UTF-16)
원칙: 원문 글자는 하나도 바꾸지 않는다. 하는 일은
 (1) XML 꾸밈(태그)을 빼고 문단·제목·게송 줄을 줄바꿈으로,
 (2) 쪽 표시만 찾기 좋은 모양으로: <pb ed="P" n="3.0001"/> → '=== Vin III 1 ===' (PTS 쪽 — PTS·BJT 판과 같은 쪽 이름이라 나란히 대조됨),
     <pb ed="M" n="0.0002"/> → '⟦M 2⟧' (6차 결집 미얀마 판 쪽), 다른 판 쪽 표시(V: VRI 데와나가리 판, T: 태국 판)는 뺌,
 (3) 다른 판본 읽기 주석 <note>…</note> 은 글자 그대로 두고 [ ] 로 감쌈 (VRI 화면과 같은 모양).
검수: verify() 가 원본 XML 의 글자(태그 뺀 것, 주석 글 포함)와 결과 글자(쪽 표시·[ ] 뺀 것)를 공백을 빼고 한 자씩 대조.
"""
import re, html, json, sys, gzip, hashlib, os
SRC = '/home/claude/vipassanatech/tipitaka-xml/romn/'
BOOKS = [('vin02m2.mul.xml', 'I', 'Mahāvaggapāḷi', '마하왁가(대품)', 'Vin-I_Mahavaggapali_VRI'),
         ('vin02m3.mul.xml', 'II', 'Cullavaggapāḷi', '쭐라왁가(소품)', 'Vin-II_Cullavaggapali_VRI'),
         ('vin01m.mul.xml', 'III', 'Pārājikapāḷi', '빠라지까', 'Vin-III_Parajikapali_VRI'),
         ('vin02m1.mul.xml', 'IV', 'Pācittiyapāḷi', '빠찟띠야', 'Vin-IV_Pacittiyapali_VRI'),
         ('vin02m4.mul.xml', 'V', 'Parivārapāḷi', '빠리와라(부수)', 'Vin-V_Parivarapali_VRI')]
ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V'}

def read(f): return open(SRC + f, encoding='utf-16').read()
def body(s): return s.split('<body xml:space="preserve">', 1)[1].rsplit('</body>', 1)[0]

def conv(f, vol):
    t = body(read(f))
    bad = []
    def pb(m):
        ed, n = m.group(1), m.group(2)
        v, p = n.split('.')
        if ed == 'P':
            if ROMAN.get(int(v)) != vol: bad.append(n)
            return f'\n=== Vin {ROMAN.get(int(v), v)} {int(p)} ===\n'
        if ed == 'M': return f'⟦M {int(p)}⟧'
        return ''
    t = re.sub(r'<pb ed="([A-Z])" n="([^"]+)"\s*/>', pb, t)
    t = re.sub(r'<note>', '[', t); t = re.sub(r'</note>', ']', t)
    gatha = lambda r: r.startswith('gatha') and r != 'gathalast'
    # 게송 줄(gatha1·2·3)은 한 줄씩, 게송 끝(gathalast)과 다른 문단 뒤에는 빈 줄
    t = re.sub(r'<p rend="(gatha[123])"[^>]*>', '', t)
    t = re.sub(r'</p>(?=\s*<p rend="gatha)', '\n', t)
    t = re.sub(r'</?(p|head|trailer|div)[^>]*>', '\n\n', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = html.unescape(t)
    t = re.sub(r'[ \t]+\n', '\n', t); t = re.sub(r'\n[ \t]+', '\n', t); t = re.sub(r'\n{3,}', '\n\n', t).strip()
    return t, bad

def canon_src(f):
    t = body(read(f)); t = t.replace('<note>', '[').replace('</note>', ']')  # 주석 [ ] 은 양쪽 모두 같게 두고 대조
    t = re.sub(r'<[^>]+>', '', t); t = html.unescape(t)
    return re.sub(r'\s+', '', t)
def canon_out(t):
    t = re.sub(r'=== Vin [IVX]+ \d+ ===', '', t); t = re.sub(r'⟦M \d+⟧', '', t)
    return re.sub(r'\s+', '', t)
def verify(f, out):
    a, b = canon_src(f), canon_out(out)
    if a == b: return 'OK', len(a)
    n = min(len(a), len(b)); i = next((i for i in range(n) if a[i] != b[i]), n)
    return f'다름 @{i}: 원문 …{a[i-30:i+30]}… / 결과 …{b[i-30:i+30]}…', len(a)

if __name__ == '__main__':
    os.makedirs('up_vri', exist_ok=True)
    head = ('Chaṭṭha Saṅgāyana Tipiṭaka (Vipassana Research Institute)\n'
            'Source: github.com/VipassanaTech/tipitaka-xml, romn/{f} (commit {c})\n\n')
    commit = open('/home/claude/vipassanatech/tipitaka-xml/.git/shallow').read().strip()[:12] if os.path.exists('/home/claude/vipassanatech/tipitaka-xml/.git/shallow') else ''
    for f, vol, name, ko, fn in BOOKS:
        t, bad = conv(f, vol)
        v, n = verify(f, t)
        pages = re.findall(r'^=== Vin [IVX]+ (\d+) ===$', t, re.M)
        out = head.format(f=f, c=commit) + t + '\n'
        open(f'up_vri/{fn}.txt', 'w', encoding='utf-8').write(out)
        with gzip.open(f'up_vri/{fn}.txt.gz', 'wb', 9) as g: g.write(out.encode())
        print(fn, '| 원문 대조:', v, f'| 글자 {n:,} | PTS 쪽 {len(pages)}개 ({pages[0]}~{pages[-1]})', '| 다른 권 쪽 표시:', bad[:5], '| M 쪽', len(re.findall('⟦M ', t)))
