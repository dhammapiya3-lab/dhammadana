"""『법구경 이야기 1』(DL-0023) 해제의 표 두 개 — 과거 스물네 분의 붓다, 붓다의 안거 장소 — 를 내려받을 그림(PNG)으로 만듦.
  python3 tools/dl0023_tables.py 책.hwp [출력 폴더]
글자·칸 합치기(rowspan·colspan)는 한글 파일의 표 그대로. 결과: <출력 폴더>/법구경이야기1_과거24붓다.png, 법구경이야기1_붓다의안거장소.png
"""
import sys, os, subprocess, html
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

src = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else '/tmp/dl0023/tables'
os.makedirs(out, exist_ok=True)
xmlp = '/tmp/dl0023/book.xml'
if not os.path.exists(xmlp):
    with open(xmlp, 'wb') as f: subprocess.run(['hwp5proc', 'xml', src], stdout=f, check=True)
root = ET.parse(xmlp).getroot()

FIXES = [('짝꾸빨라', '짝쿠빨라'), ('디팡까라', '디빵까라')]   # hwp2text_dl0023.py 의 FIXES 와 같게 (운영자가 고친 표기)

def ctext(c):
    ps = []
    for p in c.findall('Paragraph'):
        t = ''.join((x.text or '') for x in p.iter('Text') if not any(True for _ in []))
        ps.append(t.strip())
    out = '<br>'.join(html.escape(p) for p in ps if p)
    for x, y in FIXES: out = out.replace(x, y)
    return out

TABLES = {'연대': ('과거 스물네 분의 붓다', '법구경이야기1_과거24붓다'), '안거 연도': ('붓다의 안거 장소', '법구경이야기1_붓다의안거장소')}
CSS = '''body{margin:0;background:#fff;font-family:"Inter","Noto Sans CJK KR","Noto Sans KR",sans-serif;color:#222}  /* 빠알리 글자(ṅ ṁ ṭ)는 Inter 로 — 한글 글꼴의 것은 점이 어긋남 */
.w{padding:36px 40px 30px;display:inline-block}
h1{font-size:26px;margin:0 0 16px;font-weight:700}
.src{font-size:14px;color:#777;margin:0 0 18px}
table{border-collapse:collapse;font-size:17px;line-height:1.45}
th,td{border:1px solid #9c9282;padding:8px 14px;vertical-align:middle}
th{background:#efe9dc;font-weight:700;text-align:center}
td.c{text-align:center;white-space:nowrap}'''
with sync_playwright() as pw:
    br = pw.chromium.launch()
    for t in root.find('BodyText').iter('TableControl'):
        cells = list(t.iter('TableCell'))
        first = ''.join(x.text or '' for x in cells[0].iter('Text')).strip()
        if first not in TABLES: continue
        title, fname = TABLES[first]
        rows = {}
        for c in t.find('TableBody').findall('TableRow'):
            for cell in c.findall('TableCell'):
                rows.setdefault(int(cell.get('row')), []).append(cell)
        H = []
        ncol = max(int(c.get('col')) + int(c.get('colspan')) for c in cells)
        for r in sorted(rows):
            tag = 'th' if r == 0 else 'td'
            tds = []
            for cell in sorted(rows[r], key=lambda c: int(c.get('col'))):
                txt = ctext(cell); col = int(cell.get('col'))
                cls = ' class="c"' if (first == '연대' and col in (0, 1, 4)) or (first == '안거 연도' and col == 0) else ''
                rs, cs = int(cell.get('rowspan')), int(cell.get('colspan'))
                tds.append(f'<{tag}{cls}' + (f' rowspan="{rs}"' if rs > 1 else '') + (f' colspan="{cs}"' if cs > 1 else '') + f'>{txt}</{tag}>')
            H.append('<tr>' + ''.join(tds) + '</tr>')
        doc = f'<html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="w"><h1>{title}</h1><table>{"".join(H)}</table></div></body></html>'
        pg = br.new_page(device_scale_factor=2, viewport={'width': 1200, 'height': 800})
        pg.set_content(doc); pg.wait_for_timeout(300)
        path = os.path.join(out, fname + '.png')
        pg.locator('.w').screenshot(path=path)
        print(path)
    br.close()
