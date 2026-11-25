"""DL-0040 최종 교정 목록 ② 엑셀 (dl0041/xlsx.py 를 옮김, 2026-11-25)"""
import json,re
from openpyxl import Workbook
from openpyxl.styles import Font,Alignment,PatternFill
R=json.load(open('/tmp/d40fin/rows.json'))
CATS=['띄어쓰기','같은 표기 통일','맞춤법·문장부호·한자','한글 음역','따옴표·괄호','로마자','문장·내용']
R.sort(key=lambda x:(CATS.index(x['cat']),x['para'],x['pos']))
wb=Workbook(); ws=wb.active; ws.title='고친 곳'
F=Font(name='Arial',size=10); B=Font(name='Arial',size=10,bold=True); T=Font(name='Arial',size=13,bold=True)
ws['A1']='『위빠싸나 성자 아짠 문』(DL-0040) 최종 교정 목록 — 실제로 고친 곳만'; ws['A1'].font=T
ws['A2']='교정 전 본문(PDF·한글 파일에서 만든 첫 본문, 2026-11-21)에 손 교정 2곳(속표지 제목·7쪽)과 교정 목록(tools/dl0040_fixes.json 530줄 — 1회차 2026-11-22, 2회차·3회차 2026-11-25)을 차례로 적용하며 실제로 바뀐 글자를 뽑음. 다 적용한 결과가 사이트 본문과 한 글자도 다르지 않음을 확인함. 2026-11-25.'; ws['A2'].font=F
ws['A3']='굵게·기울임 표시는 빼고 보임. 짧은 고침은 앞뒤 낱말까지 넓혀 보임(빈칸 두 칸 → 한 칸 고침은 눈으로 잘 안 보일 수 있음). 한 자리를 여러 번 고친 곳·바로 옆 낱말을 함께 고친 곳은 한 줄로 묶어 처음 글 → 마지막 글로 보임. ⏎ 는 줄 바꿈. 책 소개 목차·읽기 목차의 같은 고침은 이 목록에 넣지 않음.'; ws['A3'].font=F
for c in ('A2','A3'): ws[c].alignment=Alignment(wrap_text=False)
ws.append([]); ws.append(['번호','묶음','쪽','고치기 전','고친 뒤','근거 (교정 목록 회차·줄)','곳 수'])
for c in ws[5]: c.font=B; c.fill=PatternFill('solid',start_color='E8EEF7'); c.alignment=Alignment(vertical='center',wrap_text=True)
for k,x in enumerate(R,1): ws.append([k,x['cat'],x['page'],x['before'],x['after'],x['src'],x['n']])
last=ws.max_row
for row in ws.iter_rows(min_row=6,max_row=last):
    for c in row: c.font=F; c.alignment=Alignment(vertical='top',wrap_text=True)
for col,w in zip('ABCDEFG',[6,18,10,48,48,40,7]): ws.column_dimensions[col].width=w
ws.freeze_panes='A6'; ws.auto_filter.ref=f'A5:G{last}'
s=wb.create_sheet('묶음별 합계'); s['A1']='묶음별 고친 곳 수'; s['A1'].font=T
s.append(['묶음','고친 곳 수','줄 수'])
for c in s[2]: c.font=B; c.fill=PatternFill('solid',start_color='E8EEF7')
for k,cname in enumerate(CATS,3):
    s.append([cname,f"=SUMIF('고친 곳'!$B$6:$B${last},A{k},'고친 곳'!$G$6:$G${last})",f"=COUNTIF('고친 곳'!$B$6:$B${last},A{k})"])
e=3+len(CATS); s.append(['합계',f'=SUM(B3:B{e-1})',f'=SUM(C3:C{e-1})'])
for row in s.iter_rows(min_row=3,max_row=e):
    for c in row: c.font=F
for c in s[e]: c.font=B
s.column_dimensions['A'].width=26; s.column_dimensions['B'].width=12; s.column_dimensions['C'].width=10
s[f'A{e+2}']='‘곳 수’는 고친 자리 수. 한 자리를 여러 번 고친 곳·바로 옆 낱말을 함께 고친 곳은 한 곳으로 셈. ‘같은 표기 통일’은 다르마 → 담마, 바루 → 발우, 승가 → 상가, 위빠사나 → 위빠싸나, 카르마 → 깜마, 팔리어 → 빨리어, 브라만 → 브라흐마.'; s[f'A{e+2}'].font=F
wb.save('/tmp/d40fin/out/DL-0040_최종_교정_목록.xlsx')
print(last-5)
