// 오디오북용 원고 만들기: content/texts/<ID>.json → tools/out/audiobook/<ID>/
//   node tools/audiobook_script.mjs DL-0015 [--footnotes] [--gloss]
// - 책 본문은 바꾸지 않는다. 소리로 읽을 원고만 따로 만든다.
// - 사이트 '듣기'와 같은 규칙(public/assets/app.js 의 PALI·sayable, 「빨리어 고유명사 음역 규칙」)을 그대로 불러 씀:
//   로마자 빨리어 → 한글 소리(abhiññā → 아빈냐), 한글 바로 뒤 원어 풀이(위빳사나Vipassanā)·한글 뒤 괄호 속 원어 풀이는 한 번만 읽음,
//   한자는 읽지 않음(사성제四聖諦 → 사성제), 각주 번호·쪽 표시·그림은 뺌.
// - 장(목차의 큰 항목)마다 파일 하나: 01_장제목.txt (첫 줄은 장 제목)
// - 바뀐 빨리어 목록(원문 → 소리)을 '빨리어_소리_확인.tsv' 로 남겨 사람이 검토
import fs from 'fs';
import path from 'path';

const [, , ID, ...flags] = process.argv;
if (!ID) { console.error('쓰는 법: node tools/audiobook_script.mjs DL-0015 [--footnotes] [--gloss]'); process.exit(1); }
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const app = fs.readFileSync(path.join(root, 'public/assets/app.js'), 'utf8');
const a = app.indexOf('// 빨리어 로마자 → 한글 소리'), b = app.indexOf('const fnMark');
const unBLine = app.match(/^const unB = .*$/m)[0];
const tocLine = app.match(/^const tocLines = .*$/m)[0];
const block = app.slice(a, b) + '\n' + unBLine + '\n' + tocLine + '\nreturn { PALI, sayable, LEX, langOf, PALI_MARK };';
const store = { get: (k, d) => d, set() {} };
const lib = new Function('store', 'window', block)(store, {});
const words = f => new Set(fs.readFileSync(path.join(root, 'public/data', f), 'utf8').split('\n').filter(x => x && x[0] !== '#'));
lib.LEX.pali = words('pali-words.txt'); lib.LEX.en = words('en-words.txt');

const OPT = { pali: true, gloss: flags.includes('--gloss'), en: true, hanja: false, fn: false, sym: false, paren: true, brack: true, enVoice: false };
const t = JSON.parse(fs.readFileSync(path.join(root, 'content/texts', ID + '.json'), 'utf8'));
const parts = t.body.split(/^=== (.+?) ===$/m); // [앞, 이름1, 글1, 이름2, 글2 …]
const pages = []; for (let i = 1; i < parts.length; i += 2) pages.push({ label: parts[i], text: parts[i + 1] || '' });
const top = (t.toc || []).filter(x => !x.sub && !/^\s/.test(x.title)).sort((x, y) => x.page - y.page);
const outDir = path.join(root, 'tools/out/audiobook', ID); fs.mkdirSync(outDir, { recursive: true });
for (const f of fs.readdirSync(outDir)) fs.unlinkSync(path.join(outDir, f));

const changes = new Map(); // 원문 낱말 → 소리
const LAT = /[A-Za-zÀ-ÖØ-öø-žḀ-ỿ][A-Za-zÀ-ÖØ-öø-žḀ-ỿ'’-]*/g;
const same = (x, y) => x.replace(/[\s·.,()\[\]]/g, '') === y.replace(/[\s·.,()\[\]]/g, '');
let n = 0;
const END = /([.?!…。]|[.?!][”’"」』)\]]*)$|[”’"」』]$/;
// 소리로 듣기에 맞지 않는 장(약어 표·차례·광고 목록)은 원고에서 뺌 (--all 이면 모두 넣음)
const SKIP = /^(빠알리문헌약어|약어|일러두기|차례|목차|찾아보기|색인|참고문헌|활성스님법문집〈소리문고〉)$/;
const skipped = [];
// 책에 인쇄된 철자 → 읽을 때 쓸 바른 철자 (원고에서만 바꿈)
const SPELL = [['michacārā', 'micchācārā']];

// 한글 문장 안의 로마자 풀이 빼기 (운영자 요청, 2026-11-09)
//  - 한글 바로 뒤나 한글 낱말 + 빈칸 뒤에 덧붙인 원어는 뺌: 법 dhamma이며 → 법이며, 붓당 사라낭 갓차아미 Buddhaṃ … → 뺌
//  - 한글이 섞인 괄호 안의 원어도 뺌: (아나가미 Anāgāmi) → (아나가미), [jīva 영혼] → [영혼]
//  - 한글 풀이 없이 그 자리에 원어만 쓰인 낱말(뒤에 조사가 바로 붙음)은 읽음: 1914년 Sacca-Sangaha라는, 출판사인 Sāsana …의
//  - 한글이 없는 문단(예경문·계율 문구 등)은 그대로 읽되, 주소·연도가 든 영어 서지 문단은 읽지 않음
const LC = 'A-Za-zÀ-ÖØ-öø-žḀ-ỿ';
const RUN = new RegExp(`[${LC}][${LC}'’]*(?:[ \\-.:]*[${LC}][${LC}'’]*)*-?`, 'g');
const PART = /(의|인|은|는|을|를|에|에서|한|된|및|와|과|로|으로|이라는|라는|이란)$/;
function stripGloss(s) {
  s = s.replace(/https?:\/\/\S+|www\.\S+|\S+@\S+\.\S+/g, '');
  if (!/[가-힣]/.test(s)) {                                     // 한글 없는 줄: 빨리어 줄이면 읽고, 영어·서지 줄은 뺌
    if (/\d{3,}|《|Vols?\.|ed\.|Society|Press|Publication/.test(s)) return '';
    const ws = s.match(RUN) || [];
    const en = ws.join(' ').split(/[\s\-]+/).filter(w => /^[A-Za-z]+$/.test(w) && lib.langOf(w) === 'E').length;
    const all = ws.join(' ').split(/[\s\-]+/).filter(w => w).length;
    return all && en * 2 >= all ? '' : s;
  }
  // 줄 첫머리에 두 낱말 이상 이어진 원어(계율 문구 등)는 읽음
  const lead = s.match(new RegExp(`^(?:[${LC}][${LC}'’-]*\\s+){1,}[${LC}][${LC}'’-]*`));
  if (lead) return lead[0] + stripGloss(s.slice(lead[0].length)).replace(/^(?=\S)/, ' ');
  // 한글이 든 괄호 안의 원어 빼기
  s = s.replace(/[(\[〔（［][^()\[\]〔〕（）［］]*[)\]〕）］]/g, m => /[가-힣]/.test(m) ? m.replace(RUN, '').replace(/\s*:\s*/, ' ').replace(/([(\[〔（［])\s+/, '$1').replace(/\s+([)\]〕）］])/, '$1') : m);
  s = s.replace(RUN, (m, i, all) => {
    const before = all.slice(0, i), after = all.slice(i + m.length);
    const glued = /^[가-힣]/.test(after);
    if (/[가-힣]$/.test(before)) return '';                       // 한글에 바로 붙음 → 풀이
    const w = before.match(/([가-힣]+)\s+$/);
    if (w) return glued && PART.test(w[1]) ? m : '';              // 한글 + 빈칸 뒤: 조사로 끝난 낱말 뒤 + 조사 붙음일 때만 읽음
    return glued ? m : '';                                        // 혼자 쓰인 원어: 뒤에 조사가 붙어야 읽음
  });
  return s.replace(/[ \t]{2,}/g, ' ').replace(/ ([,.)\]])/g, '$1').replace(/\(\s*\)|\[\s*\]/g, '').trim();
}
top.forEach((c, k) => {
  const from = c.page, to = (top[k + 1] ? top[k + 1].page : pages.length + 1) - 1;
  const paras = []; let lastHead = false;
  for (let p = from; p <= to; p++) {
    const txt = (pages[p - 1] || {}).text || '';
    let first = true;
    txt.split(/\n{2,}/).forEach((par, pi) => {
      par = par.trim(); if (!par) return;
      if (pi > 0 || !/\S/.test(par)) first = false;
      if (/^!\[/.test(par)) { const src = (par.match(/\]\(([^)\s]+)\)/) || [])[1]; if (t.say && t.say[src]) t.say[src].split('\n').filter(x => x.trim()).forEach(x => paras.push(lib.sayable(x, OPT))); return; }  // 그림: 소리로 읽을 글(say)이 있으면 그것만
      if (/^\[\^[^\]]+\]:/.test(par)) { if (flags.includes('--footnotes')) paras.push('각주. ' + lib.sayable(par.replace(/^\[\^[^\]]+\]:\s*/, ''), OPT)); return; }
      if (/^\|/.test(par)) return;                                    // 표
      if (/^\[\[.*\]\]$/.test(par)) return;                           // [[색인]] 같은 자리표
      // 한글과 같은 뜻으로 덧붙인 원어 풀이는 읽지 않음 (운영자 요청, 2026-11-09):
      //   괄호 ( ) [ ] 〔 〕 안에 한글이 없고 빨리어·한자·영어·숫자만 있으면 뺌 → 사성제(四聖諦), 지혜로(abhiññā), 무더기[色蘊]
      //   한글 바로 뒤에 붙은 한자·로마자도 뺌 → 사성제四聖諦, 위빳사나Vipassanā
      //   예경문처럼 빨리어만 따로 쓰였거나, 한글 풀이 없이 빨리어만 쓰인 곳은 한글 소리로 읽음
      let pre = par, prev;
      do { prev = pre; pre = pre.replace(/\s?[(\[〔（［]([^()\[\]〔〕（）［］가-힣]*)[)\]〕）］]/g, (m, inner) => /[A-Za-zÀ-ÖØ-öø-žḀ-ỿ\u3400-\u9FFF\uF900-\uFAFF]/.test(inner) ? '' : m); } while (pre !== prev);
      pre = pre.replace(/([가-힣])[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]+/g, '$1');
      // 책에 잘못 인쇄된 빨리어 철자는 읽을 때만 바른 철자로 (책 본문은 그대로) — 운영자 확인, 2026-11-09
      for (const [bad, good] of SPELL) pre = pre.split(bad).join(good);
      pre = pre.split('\n').filter(l => !(/속표지|판권지/.test(c.title) && !/[가-힣āīūṃṅñṭḍṇḷ]/.test(l))).map(stripGloss).filter(x => x).join('\n');  // 속표지·판권지의 영어 줄은 한글과 같은 내용이라 뺌
      pre = pre.replace(/[＊※]\s*/g, '').replace(/^\*\s+/gm, '').replace(/[‘’“”]/g, '').replace(/(^|\s)\S+\.(?:html?|php|aspx?)\b/g, '$1');  // 따옴표는 소리 내지 않음(조사 앞에 빈칸이 생기지 않게), 줄에 남은 주소 조각 뺌
      if (/판권지/.test(c.title)) pre = pre.split('\n').filter(l => !/주소|전화|팩스|지부|홈페이지|이메일|등록번호|ISBN|값 /.test(l)).join('\n');  // 판권지는 책 이름·판·사람·펴낸 곳만
      if (!pre.trim()) return;
      const said = lib.sayable(pre, OPT);
      (pre.match(LAT) || []).forEach(w => { const s = lib.PALI(w.replace(/[’'-]/g, '')); if (s && lib.langOf(w) !== 'E') changes.set(w, s); });
      if (!said) return;
      // 쪽이 바뀌며 끊긴 문장은 앞 문단에 이어 붙임 (쪽 첫 문단이고, 앞 문단이 문장 끝맺음 없이 끝났을 때)
      if (first && paras.length && !lastHead && !END.test(paras[paras.length - 1])) paras[paras.length - 1] += ' ' + said;
      else paras.push(said);
      lastHead = /^## /.test(par); first = false;
    });
  }
  // 장 첫머리에 장 제목과 같은 글이 또 있으면 한 번만 (사이트 듣기와 같음)
  const title = lib.sayable(c.title, OPT);
  while (paras.length && (same(paras[0], c.title) || same(paras[0], title))) paras.shift();
  if (SKIP.test(c.title.replace(/\s/g, '')) && !flags.includes('--all')) { skipped.push(c.title); return; }
  if (!paras.length && !title) return;
  n++;
  const name = String(n).padStart(2, '0') + '_' + c.title.replace(/[\u3400-\u9FFF]+/g, '').replace(/[\\/:*?"<>|]/g, '').slice(0, 40).trim() + '.txt';
  fs.writeFileSync(path.join(outDir, name), [title, ...paras].join('\n\n') + '\n');
});
const tsv = ['원문\t소리', ...[...changes].sort((x, y) => x[0].localeCompare(y[0])).map(([w, s]) => `${w}\t${s}`)].join('\n');
fs.writeFileSync(path.join(outDir, '빨리어_소리_확인.tsv'), tsv + '\n');
if (skipped.length) console.log('  원고에서 뺀 장: ' + skipped.join(', '));
console.log(`${ID}: 장 ${n}개, 빨리어 낱말 ${changes.size}개 → ${path.relative(root, outDir)}`);
