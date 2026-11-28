# 번역 교정 자료 만들기 — 『자애를 개발하는 방법』(How to Develop Metta)

작업 폴더에서(원서 PDF·한글 파일은 저장소에 두지 않음) 차례대로:

1. `pdftoppm -r 300 -gray -png 원서.pdf pg/p` → `tesseract pg/p-NN.png tsv/p-NN -l eng --psm 4 tsv` (쪽마다)
2. `hwp5txt 번역.hwp > ko.txt`
3. `python3 en_build.py` (쪽마다 문단, 쪽을 넘어간 문단 잇기) → `python3 en_fix.py` (글자 인식 오자 바로잡기 — 쪽 그림으로 확인한 것만)
4. `python3 seg.py` (문장 나누기, 글자 대조) → `python3 align.py` (LaBSE 짝짓기, pins.json: 순서를 바꿔 옮긴 목록·원서에 없는 역자 글)
5. `python3 make_doc.py` → `how-to-develop-metta.trans.json` 을 운영자에게 보내 번역 교정 화면의 '새 자료 넣기'로 올림

결과 자료(번역 글)는 비공개라 GitHub 에 올리지 않는다.
