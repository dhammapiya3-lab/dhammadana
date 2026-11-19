// 앱 연동 목록 만들기 (운영자 요청, 2026-11-17)
// 빌드가 부름 → dist/api/v1/catalog.json, dist/api/v1/books/<ID>.json
// 규격(필드 뜻·규칙)은 public/api/v1/README.md — 필드를 바꾸면 그 문서도 함께 고칠 것.
// 원칙: 없는 정보는 지어내지 않고 null. 책 본문 글자는 바꾸지 않음.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const SCHEMA_VERSION = 1;
const sha = (x, n) => { const h = crypto.createHash('sha256').update(x).digest('hex'); return n ? h.slice(0, n) : h; };
const trim = x => String(x ?? '').trim();
const nn = x => (trim(x) ? trim(x) : null);

// 라이선스 종류: 이름·설명 주소·법조문 주소·허락 범위 (CC 4.0 국제)
const CC = {
  'CC BY-NC-ND': { name_ko: '저작자표시-비영리-변경금지', commercial: false, adapt: false, share_alike: false },
  'CC BY-NC-SA': { name_ko: '저작자표시-비영리-동일조건변경허락', commercial: false, adapt: true, share_alike: true },
  'CC BY-NC': { name_ko: '저작자표시-비영리', commercial: false, adapt: true, share_alike: false },
  'CC BY-ND': { name_ko: '저작자표시-변경금지', commercial: true, adapt: false, share_alike: false },
  'CC BY-SA': { name_ko: '저작자표시-동일조건변경허락', commercial: true, adapt: true, share_alike: true },
  'CC BY': { name_ko: '저작자표시', commercial: true, adapt: true, share_alike: false },
  'CC0': { name_ko: '권리 포기', commercial: true, adapt: true, share_alike: false, no_attribution: true },
  '자유 이용(퍼블릭 도메인)': { name_ko: '자유 이용(퍼블릭 도메인)', commercial: true, adapt: true, share_alike: false, no_attribution: true }
};
const legalUrl = (code, deed) => /creativecommons\.org\/licenses\//.test(deed || '') ? deed.replace(/deed\.ko$/, 'legalcode.ko') : /publicdomain\/zero/.test(deed || '') ? 'https://creativecommons.org/publicdomain/zero/1.0/legalcode.ko' : null;

const MIME = { pdf: 'application/pdf', epub: 'application/epub+zip', hwp: 'application/x-hwp', hwpx: 'application/hwp+zip', json: 'application/json' };
const ROLE = { pdf: 'pdf_screen', pdf_print: 'pdf_print', pdf_cover: 'pdf_print_cover', epub: 'epub', hwp: 'hwp' };
const ROLE_KO = { pdf: 'PDF', pdf_print: 'PDF (인쇄용 본문)', pdf_cover: 'PDF (인쇄용 표지)', epub: 'EPUB', hwp: 'HWP (한글 파일)' };

// 사람 이름 줄('아신 떼자니야 사야도 지음')에서 역할 말을 떼어 [{name, role}] 로
const ROLES = [['지음', 'author'], ['지은이', 'author'], ['법문', 'author'], ['설법', 'author'], ['엮음', 'editor'], ['편역', 'editor_translator'], ['편저', 'editor'], ['편집', 'editor'], ['옮김', 'translator'], ['번역', 'translator'], ['한글번역', 'translator'], ['역', 'translator']];
function people(line, fallbackRole) {
  const out = [];
  for (let part of String(line || '').split(/[,，|;；]|\s{2,}/)) {
    part = part.trim(); if (!part) continue;
    let role = fallbackRole, note = null;
    const pm = part.match(/\s*\(([^()]*)\)$/); if (pm) { note = pm[1].trim(); part = part.slice(0, pm.index).trim(); }
    for (const [w, r] of ROLES) { const re = new RegExp(`\\s*${w}$`); if (re.test(part)) { role = r; part = part.replace(re, '').trim(); break; } }
    if (note) for (const [w, r] of ROLES) if (note.includes(w)) { role = r; break; }
    if (part) out.push({ name: part, role, ...(note ? { note } : {}) });
  }
  return out;
}

// 빠알리어 로마자가 본문에 많이 쓰였는지 (언어 표시는 자동 추정 — basis:'auto')
const PALI_RE = /[āīūṃṁṅñṭḍṇḷĀĪŪṂṀṄÑṬḌṆḶ]/g;

export function writeCatalog({ OUT, C, S, BOOKS, TEXTS, PARALLEL, AUDIO, HEADS, LICENSES, fileUrl, curEd, hasText, PAGES, langsOf }) {
  const SITE = S.site_url.replace(/\/$/, '');
  const abs = u => !u ? null : /^https?:\/\//.test(u) ? u : SITE + encodeURI(decodeURI(u.startsWith('/') ? u : '/' + u));
  const dir = path.join(OUT, 'api/v1'); fs.mkdirSync(path.join(dir, 'books'), { recursive: true });

  // 숨긴 책(배포 중단)도 알려 주려고 content/books 를 모두 읽음
  const all = fs.readdirSync(C('books')).filter(f => /^DL-\d{4}\.json$/.test(f)).map(f => JSON.parse(fs.readFileSync(C('books/' + f), 'utf8')));
  const shown = new Set(BOOKS.map(b => b.id));

  const licenseOf = (b, e) => {
    const code = trim(b.license);
    const k = CC[code];
    const deed = LICENSES[code] || null;
    const perm = trim(e.permission_status) || ((e.permissions || []).length ? 'confirmed' : 'unknown');
    const pub = trim(e.publisher_ebook) || trim(e.publisher_print) || null;
    const who = [trim(b.byline), trim(b.translator)].filter(Boolean).join(', ');
    const attribution = code ? `『${b.title}』${who ? ', ' + who : ''}${pub ? ', ' + pub : ''} · ${code}${k ? ` (${k.name_ko})` : ''} · 출처: ${S.site_name} ${SITE}/book/${b.id}/` : null;
    return {
      code: code || null,
      name_ko: k ? k.name_ko : (code || null),
      version: k && /^CC BY/.test(code) ? '4.0' : null,
      url: deed,
      legal_code_url: legalUrl(code, deed),
      is_cc: !!(k && /^CC/.test(code)),
      allows: k ? { share: true, commercial: k.commercial, adapt: k.adapt, share_alike: k.share_alike, attribution_required: !k.no_attribution } : null,
      attribution,
      rights_holder: null,  // 책마다 저작권자를 따로 적어 둔 자료가 아직 없음 (README '미결 사항')
      permission: perm,    // confirmed | public | pending | unknown
      permission_note: nn(e.permission_note),
      notice: nn(e.notice),
      page_url: `${SITE}/book/${b.id}/`,
      library_terms_url: `${SITE}/about/`
    };
  };

  const entries = [];
  for (const b of all) {
    const e = curEd(b);
    if (b.hidden || !shown.has(b.id)) {
      entries.push({ id: b.id, status: 'withdrawn', title: b.title });
      continue;
    }
    const lic = licenseOf(b, e);
    const okPerm = lic.permission === 'confirmed' || lic.permission === 'public';
    const files = [];
    let order = 0;
    // ① 도서관 본문 글(JSON) — 온라인 읽기·찾기·듣기에 쓰는 글
    if (hasText(b)) {
      const f = path.join(OUT, 'texts', b.id + '.json');
      const buf = fs.readFileSync(f);
      const t = TEXTS[b.id];
      const assets = [...new Set(t.pages.flatMap(p => [...p.text.matchAll(/!\[[^\]]*\]\((\/uploads\/[^)\s]+)\)/g)].map(m => m[1])).concat(Object.values(t.table_dl || {})))].map(abs);
      files.push({ file_id: 'text', role: 'text', format: 'dhammadana-text', format_version: 1, label: '도서관 본문 글 (JSON)', mime: MIME.json, url: `${SITE}/texts/${b.id}.json`, size: buf.length, sha256: sha(buf), etag: null, modified: null, required: false, order: order++, assets, uses: ['read', 'search', 'tts'] });
    }
    // ② 책 파일 (PDF·EPUB·HWP)
    for (const kind of ['epub', 'pdf', 'pdf_print', 'pdf_cover', 'hwp']) {
      const x = e[kind]; if (!x || !x.mode || x.mode === 'none' || !x.url) continue;
      const url = x.mode === 'link' || /^https?:/.test(x.url) ? x.url : fileUrl(x.url);
      const ext = (x.url.match(/\.([a-z0-9]+)$/i) || [])[1]?.toLowerCase() || kind;
      const h = HEADS[url] || {};
      files.push({ file_id: kind, role: ROLE[kind], format: ext === 'hwpx' ? 'hwpx' : kind.startsWith('pdf') ? 'pdf' : kind, label: ROLE_KO[kind], mime: MIME[ext] || MIME[kind] || null,
        url, external: x.mode === 'link', external_site: x.mode === 'link' ? nn(x.site) : undefined,
        size: h.size ?? null, sha256: null, etag: h.etag ?? null, modified: h.modified ?? null, required: false, order: order++, uses: ['read'] });
    }
    // 앱이 가장 먼저 받을 파일: 본문 글 → EPUB → 화면용 PDF
    const primary = ['text', 'epub', 'pdf'].map(id => files.find(f => f.file_id === id && !f.external)).find(Boolean);
    if (primary) primary.required = true;
    // ③ 원서 대조 짝 자료
    const parallel = (PARALLEL[b.id] || []).map(lang => {
      const f = path.join(OUT, 'parallel', `${b.id}.${lang}.json`); const buf = fs.existsSync(f) ? fs.readFileSync(f) : null;
      const ed = (b.parallel_editions || []).find(x => x.lang === lang) || {};
      return { lang, url: `${SITE}/parallel/${b.id}.${lang}.json`, size: buf ? buf.length : null, sha256: buf ? sha(buf) : null, format: 'dhammadana-parallel', format_version: 1, unit: ['paragraph', 'sentence'], original: { title: nn(ed.title), by: nn(ed.by), edition: nn(ed.edition), url: nn(ed.url) } };
    });
    // ④ 오디오북
    const a = AUDIO[b.id];
    const audiobook = a ? { human: !!a.human, url: `${SITE}/data/audio/${b.id}.json`, chapters: a.chapters.length } : null;
    // 언어 (본문 글로 추정)
    // 관리자 화면 '본문 언어'(content_languages)를 정했으면 그대로, 아니면 본문 글로 추정:
    // 로마자 글자가 한글 글자의 0.3배 넘고 빠알리 부호가 쓰였으면 빠알리어도 함께 실린 책
    let textLangs = ['ko'], basis = 'auto';
    if (Array.isArray(b.content_languages) && b.content_languages.length) { textLangs = b.content_languages.map(trim).filter(Boolean); basis = 'manual'; }
    else if (hasText(b)) {
      const all = TEXTS[b.id].pages.map(p => p.text).join('\n');
      const lat = (all.match(/[A-Za-zāīūṃṁṅñṭḍṇḷĀĪŪṂṀṄÑṬḌṆḶ]/g) || []).length, hg = (all.match(/[가-힣]/g) || []).length;
      if (lat > hg * 0.3 && (all.match(PALI_RE) || []).length >= 300) textLangs.push('pi');
    }

    const canDl = okPerm && !!lic.code;
    const entry = {
      id: b.id,
      status: 'active',
      title: b.title,
      subtitle: nn(b.subtitle),
      original_title: nn(b.original_title),
      original_languages: langsOf(b),
      byline: nn(b.byline),
      translator: nn(b.translator),
      contributors: [...people(b.byline, 'author'), ...people(b.translator, 'translator')],
      teachers: [b.teacher, ...(b.co_teachers || [])].filter(Boolean),
      edition: { label: nn(e.label), display: nn(e.label_display) || nn(e.label), published: nn(e.published), published_ebook: nn(e.published_ebook), page_count: e.page_count || null, isbn: nn(e.isbn), isbn_ebook: nn(e.isbn_ebook) },
      publisher: { print: nn(e.publisher_print), ebook: nn(e.publisher_ebook) },
      book_type: nn(b.book_type),
      topics: b.topics || [],
      description: nn(b.description),
      contents: trim(b.contents) ? trim(b.contents).split('\n').map(s => s.trimEnd().replace(/^(\s*)\*\*(.+)\*\*$/, '$1$2')) : [],
      cover: b.cover ? abs(b.cover) : null,
      page_url: `${SITE}/book/${b.id}/`,
      read_url: hasText(b) || e.reader ? `${SITE}/read/${b.id}/` : null,
      source: nn(b.original_source),
      added: nn(b.added),
      languages: { content: textLangs, basis, parallel: parallel.map(p => p.lang) },
      license: lic,
      app: {
        download: canDl,
        offline_storage: canDl,
        auto_download: canDl,
        text_extract: canDl,   // 앱 안에서 보여 주기·찾기용 (다시 배포하는 것은 license.allows 를 따름)
        tts: canDl,
        reason: canDl ? null : (!lic.code ? 'license_unknown' : 'permission_' + lic.permission)
      },
      files,
      parallel,
      audiobook
    };
    entry.license_version = sha(JSON.stringify(lic), 12);
    entry.version = sha(JSON.stringify(entry), 16);
    entries.push(entry);
  }
  entries.sort((x, y) => x.id.localeCompare(y.id));

  const about = PAGES.about ? String(PAGES.about.body || '').split('\n').find(l => l.trim() && !l.startsWith('#')) : '';
  const catalog = {
    schema: 'dhammadana-catalog',
    schema_version: SCHEMA_VERSION,
    spec_url: `${SITE}/api/v1/README.md`,
    generated: new Date().toISOString(),
    library: {
      name: S.site_name,
      name_en: 'Dhammadāna Library',
      url: SITE,
      about_url: `${SITE}/about/`,
      description: trim(about) || null,
      operator: S.publisher ? S.publisher.name : null,
      operator_url: `${SITE}/press/`,
      contact_email: S.publisher ? S.publisher.email : null,
      support_url: `${SITE}/press/support/`,
      verse: { pali: S.verse_pali, ko: S.verse_ko, cite: S.verse_cite },
      license_notice: S.footer_license
    },
    licenses: Object.fromEntries(Object.entries(CC).map(([code, k]) => [code, { name_ko: k.name_ko, url: LICENSES[code] || null, legal_code_url: legalUrl(code, LICENSES[code]) }])),
    books: entries
  };
  catalog.catalog_version = sha(JSON.stringify(catalog.books) + JSON.stringify(catalog.library), 16);
  fs.writeFileSync(path.join(dir, 'catalog.json'), JSON.stringify(catalog));
  for (const x of entries) fs.writeFileSync(path.join(dir, 'books', x.id + '.json'), JSON.stringify({ schema: catalog.schema, schema_version: SCHEMA_VERSION, generated: catalog.generated, book: x }));
  // 가벼운 변경 확인용: 책마다 version·license_version 만
  fs.writeFileSync(path.join(dir, 'versions.json'), JSON.stringify({ schema: 'dhammadana-catalog-versions', schema_version: SCHEMA_VERSION, catalog_version: catalog.catalog_version, generated: catalog.generated, books: Object.fromEntries(entries.map(x => [x.id, x.status === 'active' ? { status: x.status, version: x.version, license_version: x.license_version } : { status: x.status }])) }));
  console.log(`앱 연동 목록: 책 ${entries.filter(x => x.status === 'active').length}권 (배포 중단 ${entries.filter(x => x.status !== 'active').length}) → /api/v1/catalog.json`);
}
