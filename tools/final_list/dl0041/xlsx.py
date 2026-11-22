import json,re
from openpyxl import Workbook
from openpyxl.styles import Font,Alignment,PatternFill,Border,Side
R=json.load(open('/tmp/d41fin/rows.json'))
REN={'로마자':'로마자·빠알리 소리 줄'}
CATS=['로마자·빠알리 소리 줄','띄어쓰기','맞춤법·문장부호·한자','따옴표·괄호','한글 음역','같은 이름 통일','문장·내용','경전 출처','짜임(단락 옮기기·소제목)']
fix=lambda s:re.sub('[\U000F0000-\U000FFFFF]','(깨진 따옴표 글자)',s)
wb=Workbook(); ws=wb.active; ws.title='고친 곳'
F=Font(name='Arial',size=10); B=Font(name='Arial',size=10,bold=True); T=Font(name='Arial',size=13,bold=True)
ws['A1']='『테라와다 불교의 신행생활』(DL-0041) 최종 교정 목록 — 실제로 고친 곳만'; ws['A1'].font=T
ws['A2']='교정 전 본문(한글 파일에서 만든 첫 본문)에 교정 목록(tools/dl0041_fixes.json 532줄)을 차례로 적용하며 실제로 바뀐 글자를 뽑음. 다 적용한 결과(+ 단락 옮기기)가 사이트 본문과 한 글자도 다르지 않음을 확인함. 2026-11-22.'; ws['A2'].font=F
ws['A3']='굵게·밑줄 표시는 빼고 보임. 짧은 고침은 앞뒤 낱말까지 넓혀 보임. 한 자리를 두 번 고친 곳(예: 띄어쓰기 뒤 따옴표)·같은 낱말 안에서 붙어 고친 곳은 한 곳으로 묶어 처음 글 → 마지막 글로 보임. 17장에서 옮긴 단락(지금 140쪽) 안의 고침은 원래 쪽(157~159쪽)으로 적음.'; ws['A3'].font=F
hdr=['번호','묶음','쪽','고치기 전','고친 뒤','근거 (교정 목록 묶음·회차)','곳 수']
ws.append([]); ws.append(hdr)
for c in ws[5]: c.font=B; c.fill=PatternFill('solid',start_color='E8EEF7'); c.alignment=Alignment(vertical='center',wrap_text=True)
for k,x in enumerate(R,1):
    ws.append([k,REN.get(x['cat'],x['cat']),x['page'],fix(x['before']),fix(x['after']),x['src'],x['n']])
last=ws.max_row
for row in ws.iter_rows(min_row=6,max_row=last):
    for c in row: c.font=F; c.alignment=Alignment(vertical='top',wrap_text=True)
for col,w in zip('ABCDEFG',[6,20,12,48,48,34,7]): ws.column_dimensions[col].width=w
ws.freeze_panes='A6'; ws.auto_filter.ref=f'A5:G{last}'
s=wb.create_sheet('묶음별 합계')
s['A1']='묶음별 고친 곳 수'; s['A1'].font=T
s.append(['묶음','고친 곳 수','줄 수'])
for c in s[2]: c.font=B; c.fill=PatternFill('solid',start_color='E8EEF7')
for k,cname in enumerate(CATS,3):
    s.append([cname,f"=SUMIF('고친 곳'!$B$6:$B${last},A{k},'고친 곳'!$G$6:$G${last})",f"=COUNTIF('고친 곳'!$B$6:$B${last},A{k})"])
e=3+len(CATS)
s.append(['합계',f'=SUM(B3:B{e-1})',f'=SUM(C3:C{e-1})'])
for row in s.iter_rows(min_row=3,max_row=e):
    for c in row: c.font=F
for c in s[e]: c.font=B
s.column_dimensions['A'].width=28; s.column_dimensions['B'].width=12; s.column_dimensions['C'].width=10
s[f'A{e+2}']='‘곳 수’는 고친 자리 수. 한 자리를 두 번 고친 곳·같은 낱말 안에서 붙어 고친 곳은 한 곳으로 셈. 짜임 4줄은 단락 하나 옮김 + 소제목 셋 더함.'; s[f'A{e+2}'].font=F
wb.save('/tmp/d41fin/out/DL-0041_최종_교정_목록.xlsx')
