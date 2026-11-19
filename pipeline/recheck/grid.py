import sys,cv2,glob,os
book,sid=sys.argv[1],sys.argv[2]
out=f'/tmp/x/{sid}';os.makedirs(out,exist_ok=True)
for f in glob.glob(out+'/*'):os.remove(f)
for p in sorted(glob.glob(f'/home/claude/rev/{book}/{sid}/*.jpg')):
  im=cv2.imread(p);h,w=im.shape[:2]
  for x in range(0,w,50):cv2.line(im,(x,0),(x,h),(0,0,255) if x%100==0 else (255,180,180),1)
  for y in range(0,h,50):cv2.line(im,(0,y),(w,y),(0,0,255) if y%100==0 else (255,180,180),1)
  for x in range(0,w,100):cv2.putText(im,str(x),(x+2,12),0,.4,(0,0,255),1)
  for y in range(100,h,100):cv2.putText(im,str(y),(2,y-2),0,.4,(0,0,255),1)
  cv2.imwrite(out+'/'+os.path.basename(p),im,[cv2.IMWRITE_JPEG_QUALITY,85])
