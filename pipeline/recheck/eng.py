# 원본 영어 낱말(5자 이상) 가운데 한글 그림에 남은 것 찾기
import sys,subprocess,re,glob,os
from PIL import Image
sid=sys.argv[1]; book=sys.argv[2] if len(sys.argv)>2 else 'Vinaya-Stories'
def words(path):
    t=subprocess.run(['tesseract',path,'-','-l','eng','--psm','11'],capture_output=True,text=True).stdout
    return {w.lower() for w in re.findall(r'[A-Za-z]{5,}',t)}
n=len(glob.glob(f'/home/claude/rev/{book}/{sid}/*.jpg'))
for i in range(1,n+1):
    im=Image.open(f'/tmp/pv/{sid}/{(i+1)//2:02d}.jpg'); off=0 if i%2 else 458
    im.crop((0,off,800,off+450)).save('/tmp/_r.png')
    hit=words(f'/home/claude/rev/{book}/{sid}/{i:02d}.jpg') & words('/tmp/_r.png')
    if hit: print(i,sorted(hit))
print('eng done',n)
