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
const block = app.slice(a, b) + '\n' + unBLine + '\nreturn { PALI, sayable, LEX, langOf, PALI_MARK };';
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
top.forEach((c, k) => {
  const from = c.page, to = (top[k + 1] ? top[k + 1].page : pages.length + 1) - 1;
  const paras = [];
  for (let p = from; p <= to; p++) {
    const txt = (pages[p - 1] || {}).text || '';
    txt.split(/\n{2,}/).forEach(par => {
      par = par.trim(); if (!par) return;
      if (/^!\[/.test(par)) return;                                   // 그림
      if (/^\[\^[^\]]+\]:/.test(par)) { if (flags.includes('--footnotes')) paras.push('각주. ' + lib.sayable(par.replace(/^\[\^[^\]]+\]:\s*/, ''), OPT)); return; }
      if (/^\|/.test(par)) return;                                    // 표
      if (/^\[\[.*\]\]$/.test(par)) return;                           // [[색인]] 같은 자리표
      const said = lib.sayable(par, OPT);
      (par.match(LAT) || []).forEach(w => { const s = lib.PALI(w.replace(/[’'-]/g, '')); if (s && lib.langOf(w) !== 'E') changes.set(w, s); });
      if (said) paras.push(said);
    });
  }
  // 장 첫머리에 장 제목과 같은 글이 또 있으면 한 번만 (사이트 듣기와 같음)
  while (paras.length && same(paras[0], c.title)) paras.shift();
  const title = lib.sayable(c.title, OPT);
  if (!paras.length && !title) return;
  n++;
  const name = String(n).padStart(2, '0') + '_' + c.title.replace(/[\\/:*?"<>|]/g, '').slice(0, 40).trim() + '.txt';
  fs.writeFileSync(path.join(outDir, name), [title, ...paras].join('\n\n') + '\n');
});
const tsv = ['원문\t소리', ...[...changes].sort((x, y) => x[0].localeCompare(y[0])).map(([w, s]) => `${w}\t${s}`)].join('\n');
fs.writeFileSync(path.join(outDir, '빨리어_소리_확인.tsv'), tsv + '\n');
console.log(`${ID}: 장 ${n}개, 빨리어 낱말 ${changes.size}개 → ${path.relative(root, outDir)}`);
