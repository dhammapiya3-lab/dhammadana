# 붓다담마 법보시 도서관 – 앱 연동 명세 v1

- 명세 주소: https://dhammadana.kr/api/v1/README.md
- 확정일: 2026-11-17. 운영자: 담마삐야(我無말들). 연락처: `catalog.json` 의 `library.contact_email` (도서관 소개 페이지에도 있음)
- 이 문서는 도서관 운영자가 확정한 규칙입니다. 확정되지 않은 것은 맨 끝 '미결 사항'에 따로 적었습니다.

---

## 1. 목록 주소와 요청 방법

| 주소 | 내용 | 크기(대략) |
|---|---|---|
| `https://dhammadana.kr/api/v1/catalog.json` | 전체 목록. 도서관 정보와 모든 책 | 200KB |
| `https://dhammadana.kr/api/v1/versions.json` | 가벼운 변경 확인용. 책마다 `version`·`license_version`·`status` 만 | 5KB |
| `https://dhammadana.kr/api/v1/books/<ID>.json` | 책 한 권. catalog 의 항목과 같은 내용 | 책마다 다름 |

### 요청 방식
- 방식은 `GET` 하나입니다.
- 인증은 필요 없습니다. 열쇠나 토큰, 로그인도 쓰지 않습니다.
- 모든 주소가 `Access-Control-Allow-Origin: *` 를 보냅니다.
- 응답은 `Cache-Control: public, max-age=300` 입니다.
- 응답마다 `ETag` 가 붙습니다(Cloudflare Pages).
  - 다시 요청할 때는 `If-None-Match` 를 보내 주세요.
  - 바뀐 것이 없으면 `304 Not Modified` 가 옵니다.

### 갱신 주기
- 확인 시점:
  - 앱을 켤 때 한 번 확인합니다.
  - 앱이 계속 켜져 있으면 6시간마다 다시 확인합니다.
- 확인 순서:
  1. 먼저 `versions.json` 을 받습니다.
  2. 바뀐 책만 `books/<ID>.json` 으로 받거나, 많이 바뀌었으면 `catalog.json` 을 다시 받습니다.
- 사이트에서 책 정보나 라이선스를 고치면 약 2~5분 안에 이 주소들에 반영됩니다.
  - 사이트를 다시 만들 때(배포) 목록도 함께 만들어집니다.
  - 그래서 사이트와 앱의 라이선스 표시가 어긋나지 않습니다.
- 앱은 마지막으로 받은 `catalog.json` 을 기기에 저장해 두고 오프라인에서 그대로 씁니다.

### 주소 유지 약속
- `/api/v1/` 아래 주소와 필드 이름은 사이트 화면이나 내부 구성이 바뀌어도 그대로 유지합니다.
- 규격을 바꾸는 방법:
  - **필드를 더하는 것**은 같은 v1 안에서 합니다. 앱은 모르는 필드를 무시해야 합니다.
  - **필드를 빼거나 뜻을 바꾸는 것**은 새 주소 `/api/v2/` 로만 합니다.
  - v2 를 열면 v1 은 **최소 12개월** 그대로 둡니다.
  - 그동안 `catalog.json` 에 `deprecated` 와 `successor_url` 필드를 더해 알립니다.
- `schema_version` 이 앱이 아는 값보다 크면 앱은 목록을 갱신하지 말고 기존 목록을 계속 씁니다.

---

## 2. 목록 스키마

### 2-1. catalog.json 최상위

| 필드 | 자료형 | 필수 | 뜻 |
|---|---|---|---|
| `schema` | string | ✔ | 늘 `"dhammadana-catalog"` |
| `schema_version` | integer | ✔ | 지금 `1` |
| `spec_url` | string | ✔ | 이 문서 주소 |
| `generated` | string(ISO 8601) | ✔ | 목록을 만든 때. 내용이 같아도 배포마다 바뀜 |
| `catalog_version` | string | ✔ | 책 목록·도서관 정보의 지문(해시). **내용이 바뀔 때만 바뀜** |
| `library` | object | ✔ | 도서관 안내(아래 5장) |
| `licenses` | object | ✔ | 라이선스 종류별 이름·주소. 키는 라이선스 코드 |
| `books` | array | ✔ | 책 항목. 자료번호 순서 |

### 2-2. 책 항목 (`books[]`)

**알아보기·상태**

| 필드 | 자료형 | 필수 | 뜻 |
|---|---|---|---|
| `id` | string | ✔ | 자료번호 `DL-0001` 형식. **바뀌지 않는 고유 ID**. 제목·파일 주소가 바뀌어도 그대로 |
| `status` | string | ✔ | `active` 배포 중, `withdrawn` 배포 중단 |
| `version` | string | active 만 | 이 항목 전체(파일 정보 포함)의 지문. 무엇이든 바뀌면 바뀜 |
| `license_version` | string | active 만 | `license` 부분만의 지문. 라이선스·허락·알림이 바뀌면 바뀜 |

**책 정보**

| 필드 | 자료형 | 필수 | 뜻 |
|---|---|---|---|
| `title` | string | ✔ | 제목 |
| `subtitle` | string\|null | | 부제 |
| `original_title` | string\|null | | 원서 제목 |
| `original_languages` | string[] | ✔ | 원서의 언어(한국어 이름, 예 `["영어"]`). 없으면 빈 배열 |
| `byline` | string\|null | | 지은이 줄. 책에 적힌 그대로, 예 `"아신 떼자니야 사야도 지음"` |
| `translator` | string\|null | | 옮긴이 줄. 책에 적힌 그대로 |
| `contributors` | object[] | ✔ | 위 두 줄을 나눈 것. 아래 '사람 목록' 참고 |
| `teachers` | string[] | ✔ | 도서관 스승 목록의 아이디 |
| `edition` | object | ✔ | 지금 판. 아래 '판 정보' 참고 |
| `publisher` | object | ✔ | `{print, ebook}`. 종이책·전자책 출판사 |
| `book_type` | string\|null | | 분야(법문집·예불집·경전 등) |
| `topics` | string[] | ✔ | 주제어 |
| `description` | string\|null | | 책 소개(줄 바꿈 `\n`) |
| `contents` | string[] | ✔ | 목차 줄. 빈 줄은 묶음 사이 |
| `cover` | string\|null | | 표지 그림 주소 |
| `page_url` | string | ✔ | 사이트의 책 소개 페이지 |
| `read_url` | string\|null | | 사이트의 온라인 읽기 주소 |
| `source` | string\|null | | 원본 출처 설명 |
| `added` | string\|null | | 도서관 등록일 `YYYY-MM-DD` |
| `languages` | object | ✔ | 본문 언어. 아래 '언어' 참고 |

**권리·파일**

| 필드 | 자료형 | 필수 | 뜻 |
|---|---|---|---|
| `license` | object | ✔ | 라이선스와 이용 조건(3장) |
| `app` | object | ✔ | 앱에서 허용되는 일(3장) |
| `files` | object[] | ✔ | 받을 수 있는 파일(아래) |
| `parallel` | object[] | ✔ | 원서 대조 짝 자료. 없으면 빈 배열 |
| `audiobook` | object\|null | | `{human, url, chapters}`. 오디오북 정보 주소 |

`withdrawn` 항목에는 `id`·`status`·`title` 만 있습니다.

### 2-3. 하위 객체

**사람 목록** `contributors[]`
- `name`: 이름.
- `role`: 역할. 다음 중 하나입니다.
  - `author` 지음·법문
  - `translator` 옮김
  - `editor` 엮음
  - `editor_translator` 편역
- `note`: 선택. 괄호 속 설명, 예 `"게송 한글번역"`.
- 원문 줄(`byline`·`translator`)과 다를 수 있으므로 화면 표시는 원문 줄을 쓰기를 권합니다.

**판 정보** `edition`
- `label`: 판 이름.
- `display`: 화면에 보일 판 이름.
- `published`: 종이책 발행일(책에 적힌 글 그대로, 예 `"2009년 5월 10일"`).
- `published_ebook`: 전자책 발행일.
- `page_count`: 쪽수.
- `isbn`, `isbn_ebook`: ISBN.
- 값이 없으면 `null` 입니다.

**언어** `languages`
- `content`: 본문에 실린 언어. ISO 639 코드 배열입니다.
  - `ko` 한국어, `pi` 빠알리어, `en` 영어, `my` 미얀마어, `th` 태국어, `sa` 산스끄리뜨어.
  - 고정된 조합이 아니며, 언어가 늘 수 있습니다.
- `basis`: 언어를 정한 방법.
  - `manual`: 운영자가 정함.
  - `auto`: 본문 글을 보고 추정함. 한국어 본문에 빠알리어 로마자가 많이 실렸으면 `pi` 도 넣습니다.
- `parallel`: 원서 대조 짝 자료가 있는 언어, 예 `["en"]`.

**파일** `files[]`

| 필드 | 자료형 | 뜻 |
|---|---|---|
| `file_id` | string | 책 안에서 고유: `text` `epub` `pdf` `pdf_print` `pdf_cover` `hwp` |
| `role` | string | `text` 도서관 본문 글, `epub`, `pdf_screen` 화면용 PDF, `pdf_print` 인쇄용 본문, `pdf_print_cover` 인쇄용 표지, `hwp` 한글 파일 |
| `format` | string | `dhammadana-text`·`epub`·`pdf`·`hwp`·`hwpx` |
| `format_version` | integer | `dhammadana-text` 일 때만 (`1`) |
| `label` | string | 화면에 보일 이름 |
| `mime` | string\|null | MIME 형식 |
| `url` | string | 내려받기 주소. **만료되지 않는 고정 주소**, `Range` 요청(이어 받기) 됨 |
| `external` | boolean | `true` 면 다른 사이트의 파일입니다. 앱이 받지 말고 브라우저로 여세요 |
| `external_site` | string | external 일 때 그 사이트 이름 |
| `size` | integer\|null | 바이트. 모르면 null |
| `sha256` | string\|null | SHA-256(16진수). **지금은 `text` 파일과 짝 자료에만 있음** |
| `etag` | string\|null | 파일 저장소가 알려 준 ETag. PDF·EPUB·HWP 의 바뀜 확인용 |
| `modified` | string\|null | 파일 저장소의 마지막 수정 시각(ISO 8601) |
| `required` | boolean | `true` 인 파일 하나가 이 책의 기본 파일입니다(아래) |
| `order` | integer | 보여 줄 순서 |
| `assets` | string[] | `text` 만: 본문 속 그림 주소. 오프라인에서 그림까지 보려면 함께 받기 |
| `uses` | string[] | 이 파일의 쓰임: `read` `search` `tts` |

- **기본 파일**(`required: true`)은 아래 순서로 처음 있는 것입니다.
  1. 도서관 본문 글(`text`)
  2. EPUB
  3. 화면용 PDF
- 나머지 파일은 선택(이용자가 고를 때만 받음)입니다.
- 한 책의 파일들은 **모두 같은 판**(`edition`)입니다.
- 이전 판 파일은 목록에 넣지 않습니다.

**`dhammadana-text` 형식 (v1)**
```json
{ "book": "DL-0014", "edition": "초판",
  "pages": [ { "label": "13", "text": "…" } ],
  "toc": [ { "title": "1. 법에 대한 관심 키우기", "page": 21, "label": "13", "at": "…" } ] }
```
- `pages[].label`: 인쇄본 쪽 번호. 빈 글자면 번호 없는 쪽입니다.
- `toc[].page`: `pages` 의 1부터 세는 순번입니다. 앞에 빈칸 두 개가 있는 `title` 은 아랫단계입니다.
- `text` 는 도서관 사이트의 간단한 표시 글입니다. 문단 사이는 빈 줄입니다.
  - 문단 앞 표시:
    - `## ` 소제목
    - `:: ` 가운데 맞춤
    - `>> ` 오른쪽 맞춤
    - `^^ ` 큰 제목
    - `++ ` 들여쓰기
    - `%% ` 차례
    - `● ` 항목
    - `|| ` 이어지는 항목
  - 글 안 표시:
    - `**굵게**`, `°°기울임°°`, `==색 강조==`
    - `@@소리 줄@@`, `{{흐린 글}}`, `§§말하는 이§§`
    - 각주 `[^n]` 과 쪽 아래 `[^n]: 내용`
    - 그림 `![설명](/uploads/…)` — 설명이 `#` 으로 시작하면 화면에 보이지 않는 설명입니다.
    - 표: 줄 첫머리 `|`
  - 낭독할 때는 표시 기호를 빼고 읽으면 됩니다.
- 이 형식은 v1 안에서 표시 기호가 늘 수 있습니다. 모르는 기호는 글자 그대로 보여 주세요.

**원서 대조 짝 자료** `parallel[]`
- 필드:
  - `lang`: 원서 언어 코드.
  - `url`, `size`, `sha256`: 파일 주소·크기·지문.
  - `format: "dhammadana-parallel"`, `format_version: 1`.
  - `unit: ["paragraph","sentence"]`: 문단 묶음과 문장 짝이 모두 있다는 뜻.
  - `original`: `{title, by, edition, url}` 원서 판본 정보.
- 파일 내용:
  - `orig[]`: 원서 문단. `pg` 원서 쪽, `k` 종류(`h` 제목, `p` 문단, `sep` 구분, `toc` 차례, `gl` 용어, `pq` 크게 다시 실은 인용), `t` 글.
  - `groups[]`: 문단 묶음.
    - `ko`: 한국어 문단 열쇠 `"쪽 순번:문단 순번"`. `dhammadana-text` 의 `pages` 순번(0부터)과, 그 쪽 글을 빈 줄로 나눈 문단 순번(0부터)입니다.
    - `or`: 원서 문단 번호.
    - `s`: 문장 짝 `[[열쇠, 시작 글자, 끝 글자], [원서 문단 번호, 시작, 끝]]`.
    - `sc`: 뜻 비슷함(0~1).
- 양쪽 글자는 바꾸지 않았고, 글자 위치만 적었습니다.
- 한국어 본문 `version` 이 바뀌면 짝 자료도 함께 다시 받으세요.

### 2-4. JSON 예시

아래는 실제 목록을 줄인 것입니다(설명·목차 등은 생략).

**① 한국어 단독, 여러 파일 형식, 원서 대조(영어) 있음**
```json
{
  "id": "DL-0014", "status": "active",
  "version": "3f1c…", "license_version": "a07e…",
  "title": "알아차림만으로는 충분하지 않습니다", "subtitle": null,
  "original_title": "Awareness alone is not enough", "original_languages": ["영어"],
  "byline": "아신 떼자니야 사야도 지음", "translator": "오원탁, 이주현 옮김",
  "contributors": [
    {"name": "아신 떼자니야 사야도", "role": "author"},
    {"name": "오원탁", "role": "translator"},
    {"name": "이주현", "role": "translator"}
  ],
  "edition": {"label": "초판", "display": "초판 (전자책 교정 ver.)", "published": "2009년 5월 10일", "published_ebook": "2026년 9월 28일", "page_count": 244, "isbn": null, "isbn_ebook": "979-11-994076-5-7"},
  "publisher": {"print": "쉐우민 수행센터", "ebook": "我無말들"},
  "languages": {"content": ["ko"], "basis": "auto", "parallel": ["en"]},
  "license": {
    "code": "CC BY-NC-ND", "name_ko": "저작자표시-비영리-변경금지", "version": "4.0",
    "url": "https://creativecommons.org/licenses/by-nc-nd/4.0/deed.ko",
    "legal_code_url": "https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.ko",
    "is_cc": true,
    "allows": {"share": true, "commercial": false, "adapt": false, "share_alike": false, "attribution_required": true},
    "attribution": "『알아차림만으로는 충분하지 않습니다』, 아신 떼자니야 사야도 지음, 오원탁, 이주현 옮김, 我無말들 · CC BY-NC-ND (저작자표시-비영리-변경금지) · 출처: 붓다담마 법보시 도서관 https://dhammadana.kr/book/DL-0014/",
    "rights_holder": null, "permission": "confirmed",
    "permission_note": "이 책은 법보시용이므로 판매해서는 안됩니다.\n개인적 용도나 보시할 목적의 복사는 허가합니다.",
    "notice": "* 쉐우민 수행센터에서 … 허락받았으며 …",
    "page_url": "https://dhammadana.kr/book/DL-0014/", "library_terms_url": "https://dhammadana.kr/about/"
  },
  "app": {"download": true, "offline_storage": true, "auto_download": true, "text_extract": true, "tts": true, "reason": null},
  "files": [
    {"file_id": "text", "role": "text", "format": "dhammadana-text", "format_version": 1, "label": "도서관 본문 글 (JSON)", "mime": "application/json", "url": "https://dhammadana.kr/texts/DL-0014.json", "size": 364548, "sha256": "…", "etag": null, "modified": null, "required": true, "order": 0, "assets": ["https://dhammadana.kr/uploads/…"], "uses": ["read", "search", "tts"]},
    {"file_id": "epub", "role": "epub", "format": "epub", "label": "EPUB", "mime": "application/epub+zip", "url": "https://files.dhammadana.kr/epub/DL-0014/DL-0014_%EC%B4%88%ED%8C%90.epub", "external": false, "size": 1834221, "sha256": null, "etag": "9b2c…", "modified": "2026-11-09T03:12:40.000Z", "required": false, "order": 1, "uses": ["read"]},
    {"file_id": "pdf", "role": "pdf_screen", "format": "pdf", "label": "PDF", "mime": "application/pdf", "url": "https://files.dhammadana.kr/pdf/DL-0014/DL-0014_%EC%B4%88%ED%8C%90.pdf", "external": false, "size": 4210551, "sha256": null, "etag": "77ad…", "modified": "…", "required": false, "order": 2, "uses": ["read"]}
  ],
  "parallel": [
    {"lang": "en", "url": "https://dhammadana.kr/parallel/DL-0014.en.json", "size": 602574, "sha256": "081a…", "format": "dhammadana-parallel", "format_version": 1, "unit": ["paragraph", "sentence"],
     "original": {"title": "Awareness Alone Is Not Enough — Questions & Answers with Ashin Tejaniya", "by": "Ashin Tejaniya", "edition": "Second, revised edition May 2010 …", "url": "https://ashintejaniya.org/books-awareness-is-not-enough"}}
  ],
  "audiobook": null
}
```
(파일 크기·etag 숫자는 보기입니다.)

**② 빠알리어·한국어 함께 실린 독송집(CC BY-NC-SA), PDF·HWP**
```json
{
  "id": "DL-0027", "status": "active", "title": "빨리어 예불과 의례집",
  "languages": {"content": ["ko", "pi"], "basis": "auto", "parallel": []},
  "license": {"code": "CC BY-NC-SA", "name_ko": "저작자표시-비영리-동일조건변경허락", "version": "4.0",
    "allows": {"share": true, "commercial": false, "adapt": true, "share_alike": true, "attribution_required": true},
    "permission": "public", "…": "…"},
  "app": {"download": true, "offline_storage": true, "auto_download": true, "text_extract": true, "tts": true, "reason": null},
  "files": [
    {"file_id": "text", "required": true, "…": "…"},
    {"file_id": "pdf", "format": "pdf", "required": false, "…": "…"},
    {"file_id": "hwp", "format": "hwp", "mime": "application/x-hwp", "required": false, "…": "…"}
  ]
}
```

**③ 빠알리어 단독 자료** — 지금 도서관에는 없습니다. 생기면 `languages.content` 가 `["pi"]` 입니다(운영자가 `manual` 로 정함).

**④ 허락이 아직 확인되지 않은 책(가상의 예 — 지금은 이런 책이 없음)**
```json
{
  "id": "DL-0099", "status": "active", "title": "…",
  "license": {"code": "CC BY-NC-ND", "permission": "pending", "…": "…"},
  "app": {"download": false, "offline_storage": false, "auto_download": false, "text_extract": false, "tts": false, "reason": "permission_pending"},
  "files": ["…"]
}
```

**⑤ 배포 중단된 책**
```json
{ "id": "DL-0099", "status": "withdrawn", "title": "…" }
```

**⑥ 다른 사이트에서 받는 파일**
```json
{ "file_id": "pdf", "url": "https://…", "external": true, "external_site": "제공처 사이트", "…": "…" }
```

---

## 3. 라이선스와 이용 조건

### 3-1. `license` 객체 (책마다, 지금 판 기준)

| 필드 | 자료형 | 뜻 |
|---|---|---|
| `code` | string\|null | `CC BY-NC-ND` `CC BY-NC-SA` `CC BY-NC` `CC BY-ND` `CC BY-SA` `CC BY` `CC0` `자유 이용(퍼블릭 도메인)` `저작권자 허락` 중 하나. 없으면 null |
| `name_ko` | string\|null | 한국어 이름 |
| `version` | string\|null | CC 판 (`4.0`) |
| `url` | string\|null | 라이선스 한국어 설명 주소 |
| `legal_code_url` | string\|null | 법조문(전문) 주소 |
| `is_cc` | boolean | CC 라이선스인지 |
| `allows` | object\|null | CC 일 때만. `share` 나누기, `commercial` 영리 이용, `adapt` 고쳐 만들기, `share_alike` 같은 라이선스로만 나누기, `attribution_required` 출처 표시 필요 |
| `attribution` | string\|null | **그대로 보여 줄 출처 표기 문구** |
| `rights_holder` | string\|null | 저작권자 — 지금은 모두 null(미결 사항 1) |
| `permission` | string | 도서관 게시 허락 상태: `confirmed` 저작권자·옮긴이에게 허락받음, `public` 저작권자가 누구나 나눠도 되게 공개함, `pending` 확인 중, `unknown` 기록 없음 |
| `permission_note` | string\|null | 책에 인쇄된 허락 문구(그대로) |
| `notice` | string\|null | 운영자 알림(허락받은 경위 등) |
| `page_url` | string | 책 소개 페이지. 라이선스·허락서 그림을 온라인으로 확인하는 곳 |
| `library_terms_url` | string | 도서관 저작권 일러두기 |

### 3-2. 앱 허용 판정 `app`

| 필드 | 뜻 |
|---|---|
| `download` | 앱이 파일을 내려받아도 됨 |
| `offline_storage` | 기기에 저장해 두고 오프라인으로 읽어도 됨 |
| `auto_download` | 이용자가 고르지 않아도 앱이 미리 받아 둬도 됨 |
| `text_extract` | 앱 안에서 본문 글을 보여 주기·찾기·문단 나누기 등에 써도 됨 |
| `tts` | 앱 안에서 기계 낭독해도 됨 |
| `reason` | 허용되지 않을 때의 까닭: `license_unknown`, `permission_pending`, `permission_unknown` |

- **판정 규칙** (도서관이 계산해서 넣습니다. 앱은 이 값만 따르면 됩니다)
  - 다섯 값이 모두 `true` 가 되는 조건(모두 만족):
    1. `status` 가 `active`
    2. `license.code` 가 있음
    3. `license.permission` 이 `confirmed` 또는 `public`
  - 이 중 하나라도 아니면 다섯 값이 모두 `false` 입니다.
- 운영자 결정(2026-11-17): **허락이 확인된 모든 책은 앱 다운로드를 허락합니다.** 지금 목록의 33권은 모두 이 조건을 만족합니다.
- `text_extract`·`tts` 는 **앱 안에서 그 이용자에게 보여 주고 읽어 주는 일**까지입니다. 다음은 `license.allows` 를 따라야 합니다.
  - 고친 본문이나 변환한 파일을 앱 밖으로 내보내기(공유·다른 앱으로 보내기·파일로 저장)
  - 다시 배포하기

  예를 들어 `adapt: false`(변경 금지)인 책은 변환한 글이나 녹음 파일을 다른 사람에게 나눌 수 없습니다.
- 모든 책이 비영리입니다(`commercial: false`). **앱에 광고나 유료 결제를 붙여 이 자료를 제공하는 것은 허락 범위가 아닙니다.** (미결 사항 4)

### 3-3. 앱의 표시 의무
1. 책 정보 화면에 `license.attribution` 을 그대로 보여 주세요.
2. 라이선스 이름(`code` + `name_ko`)을 누르면 `url` 을 열어 주세요.
3. 함께 보여 줄 것:
   - `permission_note`·`notice` 가 있으면 함께 보여 주세요.
   - `page_url`(도서관 책 소개)로 가는 링크를 두세요.
4. **오프라인에서도 보여야 하는 것**: `attribution`, `code`, `name_ko`, `permission_note`, `notice`. 기기에 저장해 두세요.
5. **온라인 주소만 두면 되는 것**: `url`, `legal_code_url`, `page_url`, `library_terms_url`.
6. 앱의 도서관 안내 화면에 `library.license_notice` 를 보여 주세요.

### 3-4. 라이선스 즉시 갱신 (운영자 요구 사항)
- 운영자가 사이트에서 책의 라이선스·허락 상태·알림을 고치면, 다음 배포(약 2~5분) 때 `license` 와 `license_version` 이 바뀝니다.
- 앱이 할 일:
  1. 확인할 때마다 책별 `license_version` 을 기기에 저장한 값과 비교합니다.
  2. 다르면 `license` 를 **즉시 새 값으로 덮어쓰고** 화면에 반영합니다. 파일을 다시 받을 필요는 없습니다.
- 앱은 사이트와 다른 라이선스 정보를 자체로 갖고 있지 마세요. 늘 목록의 값을 씁니다.

### 3-5. 권리 철회·배포 중단

| 바뀐 것 | 앱이 할 일 |
|---|---|
| `status` 가 `withdrawn` 이 됨 | 그 책의 파일을 기기에서 **지우고**, 서재에 "배포가 중단된 자료입니다" 안내를 한 번 보입니다. 이용자의 메모·밑줄 같은 이용자 자료는 지우지 않습니다 |
| 목록에서 `id` 가 아예 사라짐 | `withdrawn` 과 똑같이 처리 |
| `app.download` 가 `false` 가 됨 | 새로 받기를 멈추고, 이미 받은 파일은 **지웁니다**. 안내: "권리 확인 중이라 앱에서 내려받을 수 없습니다. 사이트에서 확인해 주세요." + `page_url` |
| 라이선스가 더 좁아짐(예: SA → ND) | 파일은 그대로 두고 `license` 표시만 바꿉니다 |

---

## 4. 다운로드와 운영

### 4-1. 무엇을 받는가
- **자동으로 받는 것**: `app.auto_download: true` 인 책의 **기본 파일**(`required: true`)과 그 `assets`(그림).
  - 기본 파일은 대부분 본문 글 JSON(수백 KB)이라 서버 부담이 적습니다.
- **이용자가 고를 때만 받는 것**: PDF·EPUB·HWP 등 나머지 파일, 원서 대조 짝 자료, 오디오북 소리 파일.
  - PDF 는 수 MB~수십 MB 입니다.
- 도서관이 따로 '지정 자료'를 고르는 기능은 지금 없습니다.

### 4-2. 갱신
| 바뀐 값 | 앱이 할 일 |
|---|---|
| `version` | 그 책의 정보를 새로 고칩니다 |
| `sha256` / `etag` / `size` | 이 중 하나라도 바뀐 파일만 다시 받습니다 |
| `url` 만 바뀌고 나머지가 같음 | 파일이 그대로이므로 다시 받지 않아도 됩니다 |

- 받은 파일 옆에 받을 때의 `url`·`size`·`sha256`·`etag` 를 기록해 두세요.

### 4-3. 받기 실패와 무결성
1. 새 파일은 **임시 파일**로 받습니다.
2. 받은 뒤 확인합니다.
   - `size` 가 있으면 크기를 확인합니다.
   - `sha256` 이 있으면 SHA-256 을 확인합니다.
   - `etag` 만 있으면 응답의 `ETag` 헤더가 목록의 값과 같은지 확인합니다.
3. 확인에 통과한 경우에만 기존 파일과 바꿉니다(원자적 교체). 실패하면 임시 파일을 지우고 **기존 정상 파일을 그대로** 씁니다.
4. 이어 받기: `Range` 요청을 보내세요. `If-Range` 에 `etag` 를 넣으면 파일이 바뀌었을 때 처음부터 받게 됩니다.
5. 다시 시도: 30초 → 2분 → 10분 → 1시간 간격으로 하고, 하루에 5번까지만 합니다.
6. 서버 오류(5xx)나 연결 오류가 나도 이미 받은 책은 계속 읽을 수 있어야 합니다. 목록을 못 받으면 저장된 목록을 씁니다.

### 4-4. 접근 조건
- 인증: 없음. 공개 자료만 목록에 있습니다.
  - 학습 자료실·아카이브 같은 비공개 자료는 목록에 없고, 앞으로도 넣지 않습니다.
- 파일 주소의 만료: 없음. `files.dhammadana.kr` 의 주소는 고정입니다.
- 요청 빈도:
  - 목록 확인은 6시간에 1번 이하로 해 주세요.
  - 파일은 기기마다 동시에 2개까지만 받아 주세요.
  - 앱 쪽에서 여러 이용자의 요청을 한데 모아 대신 받는 서버(중계)를 두지 마세요. 기기가 직접 받습니다.
- `User-Agent` 에 앱 이름과 판을 넣어 주세요(예 `MyDhammaApp/1.2`). 문제가 생겼을 때 연락드리는 데 씁니다.
- 연락처: `library.contact_email` (我無말들 담마삐야)

---

## 5. 도서관 소개 (앱 안내 화면용, `catalog.json` 의 `library`)

| 필드 | 값 |
|---|---|
| `name` | 붓다담마 법보시 도서관 |
| `name_en` | Dhammadāna Library |
| `url` | https://dhammadana.kr |
| `about_url` | https://dhammadana.kr/about/ |
| `description` | 붓다담마 법보시 도서관은 부처님과 근본불교·테라와다불교 스승들의 가르침을 담은 법보시 서적을 한곳에 모아, 누구나 무료로 찾고, 내려받고, 온라인으로 읽을 수 있게 하는 곳입니다. 我無말들 출판사가 운영합니다. |
| `operator` / `operator_url` | 我無말들 / https://dhammadana.kr/press/ |
| `contact_email` | 도서관 운영자 이메일(도서관 소개 페이지에 공개된 것과 같음) |
| `support_url` | https://dhammadana.kr/press/support/ (후원 안내) |
| `verse` | Sabbadānaṃ dhammadānaṃ jināti — 법보시는 모든 보시를 능가한다 (법구경 354게송) |
| `license_notice` | 모든 자료는 무료 법보시입니다. 자료마다 표시된 라이선스(대부분 CC BY-NC-ND)를 따라 비영리로만 나누어 주세요. |

- 이 값들은 사이트 설정에서 나오므로 앱에 적어 두지 말고 목록에서 읽어 주세요.

---

## 6. 미결 사항 (도서관 운영자·권리자의 확인이 필요함)

1. **책별 저작권자**(`rights_holder`): 지금은 기록이 없어 모두 null 입니다. 허락 경위는 `notice`·`permission_note` 와 책 소개 페이지의 허락서 그림으로만 확인할 수 있습니다.
2. **앱 배포에 대한 권리자 개별 확인**:
   - 운영자는 '허락이 확인된 책은 앱 다운로드 허락'으로 정했습니다.
   - 다만 저작권자·옮긴이에게서 받은 허락이 '이 도서관 게시'만을 뜻하는지, 다른 앱에서의 배포까지 포함하는지는 책마다 다시 확인하지 않았습니다.
   - CC 라이선스 책은 라이선스 자체가 비영리 재배포를 허락합니다.
   - `저작권자 허락` 책(지금은 없음)은 앱 배포가 허락 범위 밖일 수 있습니다. 그런 책이 생기면 `app.download` 를 `false` 로 내보내도록 판정 규칙에 더할 예정입니다.
3. **PDF·EPUB·HWP 의 SHA-256**:
   - 지금은 `size`·`etag` 로만 확인합니다.
   - 파일 저장소의 ETag 는 한 번에 올린 파일이면 MD5 값이고, 나눠 올린 큰 파일이면 `…-N` 꼴이라 MD5 가 아닙니다.
   - 올릴 때 SHA-256 을 계산해 목록에 넣는 기능은 아직 없습니다.
4. **앱의 성격**: 무료·비광고 앱이어야 비영리(NC) 조건에 맞습니다. 앱의 수익 모델(광고·결제·후원 버튼 등)을 도서관 운영자에게 알려 확인받아 주세요.
5. **언어 표시**:
   - `languages.content` 는 대부분 `auto`(추정)입니다.
   - 한국어·빠알리어 대역 독송집과, 빠알리어 낱말이 많이 섞인 해설서의 구분은 운영자가 관리자 화면 '본문 언어'로 바로잡을 수 있습니다.
6. **오디오북 소리 파일의 앱 다운로드**:
   - `audiobook.url` 의 소리 파일 목록은 공개되어 있습니다.
   - 사람이 녹음한 오디오북(`human: true`)의 앱 배포 허락은 따로 확인하지 않았습니다. 확인될 때까지 앱에서는 스트리밍 재생만 권합니다.
7. **이전 판**: 지금 판만 목록에 있습니다. 이전 판을 앱에 보존할지는 정하지 않았습니다.
8. **앱에 이미 들어 있는 도서관 자료**:
   - 그 책의 `id` 와 판이 목록과 같으면 목록 규칙으로 옮기면 됩니다.
   - 판이 다르거나 목록에 없는 책은 운영자와 따로 정해 주세요.
