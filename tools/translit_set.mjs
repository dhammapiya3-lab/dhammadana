// 교정용 — 바른 한글 음역 목록 만들기 (운영자 요청, 2026-11-20)
// 사이트 '듣기'의 음역 규칙(public/assets/app.js PALI = 「빨리어 고유명사 음역 규칙」)으로
// DPD 낱말 목록(public/data/pali-words.txt)과 모든 책 본문의 로마자 낱말을 한글로 바꿔 모음.
// 결과: tools/out/translit/set.json (낱말 목록), tools/out/translit/pairs-<ID>.json (책 본문의 '한글(로마자)' 짝과 규칙 음역)
// 쓰는 법: node tools/translit_set.mjs [책 ID]
import fs from 'fs'; import path from 'path';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const app = fs.readFileSync(root + '/public/assets/app.js', 'utf8');
const a = app.indexOf('// 빨리어 로마자 → 한글 소리'), b = app.indexOf('const fnMark');
const unBLine = app.match(/^const unB = .*$/m)[0], tocLine = app.match(/^const tocLines = .*$/m)[0];
const lib = new Function('store', 'window', app.slice(a, b) + '\n' + unBLine + '\n' + tocLine + '\nreturn { PALI };')({ get: (k, d) => d, set() {} }, {});
const out = root + '/tools/out/translit'; fs.mkdirSync(out, { recursive: true });
const S = new Set();
const add = w => { try { const k = lib.PALI(w); if (k && /^[가-힣 ]+$/.test(k)) S.add(k.replace(/\s/g, '')); } catch (e) {} };
for (const l of fs.readFileSync(root + '/public/data/pali-words.txt', 'utf8').split('\n')) if (l && l[0] !== '#') add(l);
const LAT = /[A-Za-zĀāĪīŪūṬṭḌḍṆṇṄṅÑñṂṃṀṁḶḷ]+/g;
for (const f of fs.readdirSync(root + '/content/texts')) { const t = JSON.parse(fs.readFileSync(root + '/content/texts/' + f, 'utf8')); for (const w of (t.body.match(LAT) || [])) if (w.length > 2) add(w); }
fs.writeFileSync(out + '/set.json', JSON.stringify([...S]));
const ID = process.argv[2];
if (ID) {
  const t = JSON.parse(fs.readFileSync(root + '/content/texts/' + ID + '.json', 'utf8'));
  const pages = t.body.split(/^=== (.+?) ===$/m); const pairs = [];
  for (let i = 1; i < pages.length; i += 2) {
    const tx = pages[i + 1].replace(/\*\*|°°|==|\[\^[^\]]*\]/g, '');
    for (const m of tx.matchAll(/([가-힣]+(?: [가-힣]+){0,2})\(([A-Za-zĀāĪīŪūṬṭḌḍṆṇṄṅÑñṂṃṀṁḶḷ][A-Za-zĀāĪīŪūṬṭḌḍṆṇṄṅÑñṂṃṀṁḶḷ \-]*)[,)]/g)) {
      let k = ''; try { k = m[2].split(/[ -]/).map(w => lib.PALI(w) || '').join(''); } catch (e) {}
      pairs.push([pages[i], m[1], m[2], k]);
    }
  }
  fs.writeFileSync(out + '/pairs-' + ID + '.json', JSON.stringify(pairs));
}
console.log('바른 음역 낱말', S.size);
