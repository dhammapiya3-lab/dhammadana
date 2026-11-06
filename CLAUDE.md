# 테라와다불교 법보시 도서관 (dhammadana.kr)

운영자: 담마삐야(我無말들 출판사). 컴퓨터 작업에 익숙하지 않으니 **쉬운 한국어로, 단계별로** 설명할 것.

## 구조
- 정적 사이트. `npm run build` → `node build.mjs` 가 `content/` 를 읽어 `dist/` 를 만든다. 프레임워크 없음.
- 호스팅: Cloudflare Pages (빌드 명령 `npm run build`, 출력 `dist`). main 에 push 하면 자동 배포.
- 큰 파일(PDF·EPUB·쪽 그림): Cloudflare R2, 주소 `https://files.dhammadana.kr/` (`content/settings.json` 의 files_base).
  - `pdf/<ID>/<ID>_<판>.pdf`, `epub/<ID>/...`, `reader/<ID>/<판>/manifest.json` + `p/0001.webp`, `big/0001.webp`
- 관리자 화면: `/admin`, 책 파일 올리기: `/admin/upload/` (functions/api/upload.js, R2 바인딩 FILES — wrangler.toml)
- 화면 동작: `public/assets/app.js`, 디자인: `public/assets/site.css`.

## 자료 (content/)
- `books/DL-0001.json` … 책 하나 = 파일 하나. 판(editions) 중 `current: true` 인 것만 내려받기·읽기에 쓴다. 이전 판은 지우지 않는다.
- `teachers.json`, `traditions.json`, `topics.json`(main + items{label,group}), `providers.json`, `permissions.json`, `links.json`, `playlists.json`(RSS는 빌드 때 가져옴), `variants.json`(검색 표기 사전), `settings.json`
- `pages/*.md`, `news/*.md` (앞머리 + 마크다운)

## 원칙
- 빨리어 표기: 프로젝트 문서 「빨리어 고유명사 음역 규칙」(니까야 번역 용어집 v1.1). 일반 용어는 위빳사나·사띠빳타나, **책 제목·책에 인쇄된 이름은 책 표기 그대로**, 스승 이름 -vaṃsa 는 ‘왐사’. 다른 표기는 teachers.aliases 와 variants.json 에.
- 없는 정보를 지어내지 않는다 (책 소개·파일이 없으면 "준비 중").
- 이메일 등 개인정보는 사이트 표기 외 다른 곳에 보내지 않는다.

## 자주 하는 일
- **PDF를 도서관 책으로 (지금 방식)**: `python3 tools/pdf2reader.py 책.pdf DL-0007 개정판 --offset N --toc toc.txt` → 원문 대조 ✓ 확인 — 보통 `--visible-only --footnotes --headings --visual-order --line-breaks` 를 붙이고 manifest2text 에는 `--keep-order` (숨은 옛 글 빼기·각주 [^n] 표시·큰 글씨 줄을 ## 소제목으로·인쇄된 위→아래 순서 지키기). **순서·내용을 임의로 바꾸지 말 것** — 인쇄된 순서가 기준. 목차 파일은 '제목<TAB>쪽', 아랫단계는 줄 앞에 빈칸 두 개. out/…/hidden.txt 확인. manifest2text 에 `--header "쪽 머리글"` 을 주면 머리글을 뺀다 → `python3 tools/manifest2text.py tools/out/reader/<ID>/<판>/manifest.json` 로 `content/texts/<ID>.json` 을 만들어 commit (이 글 파일이 있으면 글로 읽기가 켜짐, 관리자 화면 '책 본문'에서 고칠 수 있음). PDF 파일은 운영자가 /admin/upload/ 에서 올림. 읽기 화면은 글로 보기만 씀.
- **(예전 방식)**: `python3 tools/pdf2reader.py 책.pdf DL-0007 초판 [--offset N] [--toc toc.txt]` → 결과 확인(깨진 빨리어 글자 경고 확인) → `python3 tools/upload.py` → 책 JSON 의 해당 판에서 `reader: true`, `pdf: {mode: file, url: pdf/DL-0007/DL-0007_초판.pdf}` → commit·push.
- 새 책: `content/books/` 에 다음 번호로 파일 추가(형식은 기존 파일 참고), 표지는 `public/covers/<ID>.jpg`.
- 확인: `npm run dev` → http://localhost:4321
