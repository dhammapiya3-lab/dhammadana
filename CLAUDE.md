# 테라와다불교 법보시 도서관 (dhammadana.kr)

운영자: 담마삐야(我無말들 출판사). 컴퓨터 작업에 익숙하지 않으니 **쉬운 한국어로, 단계별로** 설명할 것.

## 구조
- 정적 사이트. `npm run build` → `node build.mjs` 가 `content/` 를 읽어 `dist/` 를 만든다. 프레임워크 없음.
- 호스팅: Cloudflare Pages (빌드 명령 `npm run build`, 출력 `dist`). main 에 push 하면 자동 배포.
- 큰 파일(PDF·EPUB·쪽 그림): Cloudflare R2, 주소 `https://files.dhammadana.kr/` (`content/settings.json` 의 files_base).
  - `pdf/<ID>/<ID>_<판>.pdf`, `epub/<ID>/...`, `reader/<ID>/<판>/manifest.json` + `p/0001.webp`, `big/0001.webp`
- 관리자 화면: `/admin`, 책 파일 올리기: `/admin/upload/` (functions/api/upload.js, R2 바인딩 FILES — wrangler.toml)
- 종이책 보시 신청 게시판(비밀글): `/press/request/` (public/assets/paper.js), 서버 `functions/api/paper.js`, 저장은 공개 주소 없는 R2 `PAPER` 창고(dhammadana-paper), 관리 `/admin/paper/`. 알림 메일은 Pages 비밀 변수 PAPER_NOTIFY_URL(운영자 Gmail 의 구글 Apps Script 웹 앱)로 보냄. 신청 개인정보는 다른 곳에 보내거나 저장하지 않는다. 책의 `paper` 값: request(보시 신청)·soldout(품절)·ebook(전자책 Only).
- 사이트 통계: `/admin/stats/` (functions/api/stats.js). 방문 기록은 app.js 가 `/api/hit`(functions/api/hit.js)로 보내 PAPER 창고 `stats/` 에 저장 — 기기별 무작위 번호만, IP·이름 저장 안 함. 지난 날은 `stats/day/<날짜>.json` 으로 묶고 낱개는 지움. 관리자 기기는 localStorage `dd-notrack` 이 true 면 보내지 않음(/admin 들어가면 저절로 켜짐).
- 회원(독서 기록 이어 보기): `/account/` (app.js 의 initAccount·syncNow), 서버 `functions/api/account.js`, 저장은 PAPER 창고 `acct/`. 아이디+비밀번호(되돌릴 수 없게 바꾼 값만), 비밀번호 찾기는 복구 코드(모든 회원) 또는 이메일(넣은 회원만, PAPER_NOTIFY_URL 의 Apps Script 가 `to` 로 보냄). 아이디 찾기는 이메일로(`find_id`, 색인 `acct/emails/<해시>.json` — 이메일 자체가 아닌 해시를 이름으로, 있든 없든 같은 대답). Apps Script 는 Pages 비밀 변수 PAPER_NOTIFY_KEY 와 같은 KEY 를 확인함. 운영자도 비밀번호·복구 코드를 볼 수 없음. 이어 보는 것: bm·ul·hist·pos-·ppos-·plast·pl·sub- (키마다 나중에 바꾼 것이 이김, 기기에서 처음 로그인할 때 책갈피·밑줄·내 서재는 합침). 이메일은 비밀번호 찾기 메일 말고 쓰지 않는다.
- 학습 자료실(`/study/`, Cloudflare Access 로 허락받은 분만): 파일은 비공개 R2 `MEMBERS`(dhammadana-study). 법보시 도서관처럼 찾아보기(출판사·책 형식·주제)+표지 카드+자료 소개 화면(app.js initMembers). 자료마다의 정보(제목·출판사·형식·주제·소개·파일·표지)는 **공개 GitHub 에 두지 않고** MEMBERS 의 `_catalog.json` 에 저장, 관리 화면 `/admin/members/` 의 '자료 정보'에서 입력. 분류 틀(출판사·형식 목록)은 `content/study.json`, 주제는 topics.json 그대로.
- 화면 동작: `public/assets/app.js`, 디자인: `public/assets/site.css`.

## 자료 (content/)
- `books/DL-0001.json` … 책 하나 = 파일 하나. 판(editions) 중 `current: true` 인 것만 내려받기·읽기에 쓴다. 이전 판은 지우지 않는다.
- `teachers.json`, `traditions.json`, `topics.json`(main + items{label,group}), `providers.json`, `permissions.json`, `links.json`, `playlists.json`(RSS는 빌드 때 가져옴), `variants.json`(검색 표기 사전), `settings.json`
- `pages/*.md`, `news/*.md` (앞머리 + 마크다운)
- `indexes/<ID>.json`: 색인처럼 표로 된 책의 표 자료(인쇄본의 부마다 cols·rows 를 인쇄 순서 그대로). 글로 읽기 본문의 `[[색인]]` 자리에 찾기 칸과 순서 버튼(부 바꾸기)이 있는 표로 보이고(휴대폰은 낱말 카드), 사이트 검색에도 잡힌다. 예: DL-0004 『빠알리어-한국어-영어 색인』. 표가 차지하는 쪽은 본문에 빈 쪽 표시(=== N쪽 ===)만 둔다.

## 원칙
- 빨리어 표기: 프로젝트 문서 「빨리어 고유명사 음역 규칙」(니까야 번역 용어집 v1.1). 일반 용어는 위빳사나·사띠빳타나, **책 제목·책에 인쇄된 이름은 책 표기 그대로**, 스승 이름 -vaṃsa 는 ‘왐사’. 다른 표기는 teachers.aliases 와 variants.json 에.
- 없는 정보를 지어내지 않는다 (책 소개·파일이 없으면 "준비 중").
- 이메일 등 개인정보는 사이트 표기 외 다른 곳에 보내지 않는다.

## 자주 하는 일
- **PDF를 도서관 책으로 (지금 방식)**: `python3 tools/pdf2reader.py 책.pdf DL-0007 개정판 --offset N --toc toc.txt` → 원문 대조 ✓ 확인 — 보통 `--visible-only --footnotes --headings --visual-order --line-breaks` 를 붙이고 manifest2text 에는 `--keep-order` (숨은 옛 글 빼기·각주 [^n] 표시·큰 글씨 줄을 ## 소제목으로·인쇄된 위→아래 순서 지키기). **순서·내용을 임의로 바꾸지 말 것** — 인쇄된 순서가 기준. 목차 파일은 '제목<TAB>쪽', 아랫단계는 줄 앞에 빈칸 두 개. out/…/hidden.txt 확인. manifest2text 에 `--header "쪽 머리글"` 을 주면 머리글을 뺀다 → `python3 tools/manifest2text.py tools/out/reader/<ID>/<판>/manifest.json` 로 `content/texts/<ID>.json` 을 만들어 commit (이 글 파일이 있으면 글로 읽기가 켜짐, 관리자 화면 '책 본문'에서 고칠 수 있음). PDF 파일은 운영자가 /admin/upload/ 에서 올림. 읽기 화면은 글로 보기만 씀.
- **책 맨 앞(1쪽 첫머리)에 인쇄된 책 제목은 글로 읽기 본문과 목차에서 뺀다** (운영자 요청, 2026-11). 목차는 예경문 등 본문 첫 부분부터 시작. manifest2text 에 `--drop-title "책 제목"`. **단, 제목·저자·발행 정보만 따로 인쇄된 속표지 쪽은 책 제목을 지우지 않고 그대로 두고 '속표지' 장으로 둔다** (운영자 요청, 2026-11). 지우는 것은 예경문 등 다른 글 위에 함께 인쇄된 제목뿐.
- **장 제목 정하기**: 책에 인쇄된 장 제목이 있으면 그대로 쓰고, 없으면 '예경문'·'저자 소개'·'역자 소개'·'머리말'·'일러두기'·'차례'·'발원문'·'회향'·'판권지'처럼 알맞은 일반 이름을 쓴다. **본문의 첫 줄(사람 이름, 첫 문장 등)을 장 제목으로 쓰지 않는다** (운영자 요청, 2026-11).
- **성격이 다른 부분은 늘 따로 나눈다**: 예경문·저자 소개·역자 소개·머리말(서문)·일러두기·차례·본문·발원문·회향·판권지는 각각 다른 장(화면)으로 나눈다. 같은 쪽에 함께 인쇄돼 있으면 목차 항목의 at(쪽 중간 시작)으로 나눈다 (운영자 요청, 2026-11).
- **장(챕터)이 바뀌면 늘 새 쪽에서 시작** (운영자 요청, 2026-11-09): 쪽 번호(=== N쪽 ===)가 있는 책에서 큰 목차 항목(장)이 쪽 중간에서 시작하면, 그 자리에 같은 쪽 이름의 쪽 표시를 하나 더 넣어 앞 장의 글과 나눈다(at 대신). 쪽 번호를 넣거나 목차를 고친 뒤에는 늘 `python3 tools/split_chapters.py --write` 를 돌린다. **쪽 표시는 절대 제목·소제목 줄 중간에 넣지 않는다**(예: `## II` / `=== 207쪽 ===` / `I. 생각의 양식` 처럼 갈라지면 안 됨) — 장 제목 줄은 쪽 표시 바로 다음에 온전히. 장 이름은 책에 인쇄된 번호까지 그대로(예: 'III. 생각의 양식').
- **장 제목과 같은 소제목은 장 제목으로 통일** (운영자 요청, 2026-11-09): 장 첫머리에 장 제목과 같은 글(## 소제목, 가운데 큰 제목 등)이 또 있으면 글로 읽기 화면에서는 위의 큰 장 제목 하나만 보이고(본문 쪽 글은 숨김, 글자는 지우지 않음), 듣기는 장이 시작할 때 장 제목을 먼저 읽고 본문의 같은 제목은 건너뜀 — app.js 의 chDups(장 첫머리의 문단 몇 개를 이어 붙인 것('Ⅳ' + '위빳사나 지혜의 초석')도, 띄어쓰기·마침표·괄호 차이는 무시하고 같으면 숨김). 그래서 장 이름(목차의 큰 항목)은 책에 인쇄된 제목과 같게 짓는다.
- **인쇄본의 그림은 기본으로 넣는다** (운영자 요청, 2026-11): 본문에 들어간 사진·그림·삽화·상징(법륜 등)은 인쇄된 자리 그대로 글로 읽기에도 넣는다 — PDF 쪽을 높은 배율로 그려서 그림 부분만 잘라 `public/uploads/<ID>-이름.jpg|png` 로 두고 본문에 `![#설명](/uploads/…)` (책에 설명 글이 없으면 # 을 붙여 화면에 안 보이게), 텍스트 JSON 의 images 목록에도 추가. 글 뒤에 깔린 바탕 무늬·배경 그림은 빼되, 빼거나 애매한 것은 운영자에게 알린다.
- **인쇄본에서 굵게 강조된 글자는 굵게 표시** (운영자 요청, 2026-11): 소제목(## 줄) 말고 본문·게송·판권지 등에서 굵은 글꼴(Bold·Heavy·SemiBold·PB 등, Medium 은 뺌)로 인쇄된 곳은 본문에 `**글**` 로 감싼다 → `python3 tools/mark_bold.py <ID> 책.pdf` 로 미리 보고 `--write` 로 적용 (글자는 그대로, ** 만 더함). 본문보다 큰 짧은 굵은 글(장 제목·쪽 번호)은 건드리지 않는다. 관리자 화면 '책 본문'에서도 글을 골라 'B 굵게' 단추로 넣고 뺄 수 있다.
- **색 강조·속표지 제목** (운영자 요청, 2026-11): 원본에서 색 글자(하늘색 등)로 강조한 곳은 `==글==` 로 감싼다 → 글로 읽기에서 원본 하늘색(#00aeef)으로 보임. 속표지의 책 제목 문단은 앞에 `^^ ` 를 붙이면 크게·가운데로 보인다. 크기는 그대로 가운데 맞춤만 할 문단은 앞에 `:: `. `● ` 로 시작하는 문단은 다음 줄들이 ● 만큼 들여써지고, 쪽이 넘어가 이어지는 항목 문단은 앞에 `|| ` 를 붙여 같은 만큼 들여쓴다.
- **문단 나눔도 인쇄본과 맞춘다**: 인쇄본에서 들여쓰기로 시작하거나 빈 줄 뒤에 오는 줄은 새 문단(빈 줄), 꽉 찬 줄 다음의 들여쓰지 않은 줄은 같은 문단(이어 붙임). 번호 목록(1. 2) ①)·게송 줄은 줄마다 나눈다. 쪽이 넘어가는 문단은 이어 붙인다.
- **완성 후 검수는 기본** (운영자 요청, 2026-11): 책 본문을 만들거나 고친 뒤에는 늘 검수하고 결과를 알린다 — ① 글자: 원문과 한 자도 다르지 않은지(pdf2reader 의 ✓, 고친 전후 글자 수 대조) ② 순서·줄 바꿈·각주: `python3 tools/audit_text.py <ID> 책.pdf` (게송·잠언·판권지 줄은 인쇄본과 같게, 산문은 이어 붙여도 됨) ③ 숨은 글(hidden.txt)·장 나눔·그림 위치를 화면으로 확인 ④ 다른 점은 고친 것과 일부러 다르게 한 것을 나눠서 보고.
- **(예전 방식)**: `python3 tools/pdf2reader.py 책.pdf DL-0007 초판 [--offset N] [--toc toc.txt]` → 결과 확인(깨진 빨리어 글자 경고 확인) → `python3 tools/upload.py` → 책 JSON 의 해당 판에서 `reader: true`, `pdf: {mode: file, url: pdf/DL-0007/DL-0007_초판.pdf}` → commit·push.
- 새 책: `content/books/` 에 다음 번호로 파일 추가(형식은 기존 파일 참고), 표지는 `public/covers/<ID>.jpg`.
- 검색엔진: 빌드가 `sitemap.xml`·`robots.txt` 를 만든다(관리자·회원·학습 자료실·내 서재·검색 화면과 noindex 페이지는 뺌).
- 확인: `npm run dev` → http://localhost:4321
