// 인공지능 목소리(Supertonic 3) 듣기 시험 — 문단마다 목소리를 만들어 음악처럼 이어서 재생
import { ort, loadTextToSpeech, loadVoiceStyle, writeWavFile, setOnBytes, CACHE_NAME } from './helper.js';

const REV = 'aafc6e32416a594460b32413efc49d7fe4ce6d46';
const HF = `https://huggingface.co/supertone-oss-archive/supertonic-3/resolve/${REV}`;
const ONNX = `${HF}/onnx`;
const AHEAD = 4;  // 미리 만들어 둘 문단 수

const $ = s => document.querySelector(s);
const player = $('#player');
const SILENT = URL.createObjectURL(new Blob([writeWavFile(new Array(4410).fill(0), 44100)], { type: 'audio/wav' }));
const S = { tts: null, style: null, styleId: '', backend: '', items: [], gen: 0, play: 0, ready: new Map(), run: 0, stalls: 0, done: 0, rtf: [], waiting: false, hiddenAt: 0, hiddenLast: 0 };

// ---------- 기록 ----------
const t0 = Date.now();
const stamp = () => { const s = Math.round((Date.now() - t0) / 1000); return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`; };
function log(m) { const el = $('#log'); el.textContent += `[${stamp()}] ${m}\n`; el.scrollTop = el.scrollHeight; }
const status = (m, cls) => { const el = $('#status'); el.textContent = m; el.className = 'status ' + (cls || ''); };
const bar = p => { $('#bar').style.width = Math.max(0, Math.min(100, p)) + '%'; };
function stats() {
  $('#sBackend').textContent = S.backend || '—';
  $('#sAhead').textContent = Math.max(0, S.gen - S.play);
  $('#sStall').textContent = S.stalls;
  $('#sDone').textContent = S.done;
  if (S.rtf.length) { const r = S.rtf.reduce((a, b) => a + b, 0) / S.rtf.length; $('#sRtf').innerHTML = `<span class="${r >= 1 ? 'good' : 'bad'}">${r.toFixed(2)}배</span>`; }
}
log(`기기: ${navigator.userAgent}`);
log(`화면 격리(여러 일꾼 계산): ${self.crossOriginIsolated ? '켜짐' : '꺼짐'} · 처리 장치 ${navigator.hardwareConcurrency || '?'}개 · WebGPU ${'gpu' in navigator ? '있음' : '없음'}`);

// ---------- 모델 받기 ----------
ort.env.wasm.wasmPaths = new URL('./ort/', import.meta.url).href;
ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 1) : 1;

async function hasCache() { try { const c = await caches.open(CACHE_NAME); return !!(await c.match(`${ONNX}/vector_estimator.onnx`)); } catch (e) { return false; } }
(async () => { status((await hasCache()) ? '모델이 이 기기에 저장되어 있습니다. [모델 받기 · 준비]를 누르면 바로 준비됩니다.' : '아직 모델을 받지 않았습니다. 와이파이에서 [모델 받기 · 준비]를 눌러 주세요.'); })();

let fileNo = 0;
const FILES = ['tts.json', 'duration_predictor.onnx', 'text_encoder.onnx', 'vector_estimator.onnx', 'vocoder.onnx', 'unicode_indexer.json'];
setOnBytes((got, total, name) => {
  const i = FILES.indexOf(name); if (i >= 0) fileNo = i;
  const mb = (got / 1048576).toFixed(0), tmb = total ? (total / 1048576).toFixed(0) : '?';
  status(`받는 중 (${fileNo + 1}/${FILES.length}) ${name} — ${mb} / ${tmb} MB`);
  bar(((fileNo + (total ? got / total : 0)) / FILES.length) * 100);
});

$('#loadBtn').onclick = async () => {
  $('#loadBtn').disabled = true; $('#ep').disabled = true;
  try { if (navigator.storage && navigator.storage.persist) log(`저장 공간 지키기 요청: ${(await navigator.storage.persist()) ? '허락됨' : '허락 안 됨(나중에 지워질 수 있음)'}`); } catch (e) {}
  const tic = Date.now();
  const tryLoad = async ep => { const r = await loadTextToSpeech(ONNX, { executionProviders: [ep], graphOptimizationLevel: 'all' }); S.tts = r.textToSpeech; S.backend = ep === 'webgpu' ? 'WebGPU (그래픽 장치)' : `WebAssembly (처리 장치 ${ort.env.wasm.numThreads}개)`; };
  try {
    const ep = $('#ep').value; log(`계산 방식 선택: ${ep}`);
    if (ep === 'wasm') await tryLoad('wasm');
    else if (ep === 'webgpu') await tryLoad('webgpu');
    else if ('gpu' in navigator) { try { await tryLoad('webgpu'); } catch (e) { log('WebGPU 를 쓸 수 없어 WebAssembly 로 바꿉니다: ' + e.message); await tryLoad('wasm'); } }
    else await tryLoad('wasm');
    bar(100); status(`준비됐습니다 (${((Date.now() - tic) / 1000).toFixed(0)}초). 글을 고르고 [듣기 시작]을 눌러 주세요.`, 'good');
    log(`모델 준비 완료 · ${S.backend} · ${((Date.now() - tic) / 1000).toFixed(1)}초`);
    $('#playBtn').disabled = false; stats();
  } catch (e) {
    status('모델을 준비하지 못했습니다: ' + e.message, 'bad'); log('오류: ' + (e.stack || e.message)); $('#loadBtn').disabled = false;
  }
};
$('#clearBtn').onclick = async () => {
  if (!confirm('이 기기에 저장한 목소리 모델(약 400MB)을 지울까요? 다음에 다시 받아야 합니다.')) return;
  try { await caches.delete(CACHE_NAME); status('저장한 모델을 지웠습니다.'); log('저장한 모델 지움'); } catch (e) { status('지우지 못했습니다: ' + e.message, 'bad'); }
};

// ---------- 읽을 글 ----------
const PALI = [
  '나모 땃사 바가와또 아라하또 삼마삼붓닷사.',
  '사띠빳타나 수행에서는 사띠와 삼빠잔냐가 중요합니다.',
  '위빳사나 수행자는 아닛짜, 둑카, 아낫따를 있는 그대로 봅니다.',
  '로바, 도사, 모하가 일어나면 일어난 줄 알아차립니다.',
  '아신 떼자니야 사야도께서는 마음가짐이 바르게 되었을 때 수행하라고 하셨습니다.',
  '요니소 마나시까라가 있으면 꾸살라가 일어나고, 아요니소 마나시까라가 있으면 아꾸살라가 일어납니다.',
  '삿다, 위리야, 사띠, 사마디, 빤냐를 오력이라고 합니다.',
  '이 책은 2025년 8월 1일에 전자책으로 나왔습니다.'
];
// 화면용 표시(굵게·색·각주 번호 등)와 괄호 속 원어·한자는 빼고 읽음
function clean(p) {
  let t = p.replace(/^(?:## |\^\^ |:: |\|\| )/gm, '').replace(/\*\*|==/g, '').replace(/\[\^[^\]]+\]/g, '');
  t = t.replace(/\s?[(（][^()（）]*[A-Za-zĀ-ž一-鿿][^()（）]*[)）]/g, '');
  return t.replace(/\s*\n\s*/g, ' ').replace(/\s{2,}/g, ' ').trim();
}
const usable = p => p.trim() && !/^\[\^[^\]]+\]:/.test(p) && !/^!\[/.test(p) && !/^\|/.test(p.trim()) && !/^\[\[/.test(p.trim());
let BOOK = null;
async function loadBook(id) {
  const r = await fetch(`/texts/${id}.json`); BOOK = await r.json();
  const chs = BOOK.toc.filter(t => !/^\s/.test(t.title));
  $('#chap').innerHTML = chs.map((t, i) => `<option value="${i}">${t.title}${t.label ? ` (${t.label}쪽)` : ''}</option>`).join('');
  const first = chs.findIndex(t => !/속표지|예경문|저자|목차|차례|판권/.test(t.title)); if (first >= 0) $('#chap').value = first;
}
function chapterParas() {
  const chs = BOOK.toc.filter(t => !/^\s/.test(t.title)), i = +$('#chap').value;
  const from = chs[i].page - 1, to = (chs[i + 1] ? chs[i + 1].page - 1 : BOOK.pages.length);
  const out = [];
  let cut = false;  // 앞 쪽 끝에서 문장이 끊겼으면 다음 쪽 첫 문단과 이어 읽기
  for (let n = from; n < to; n++) {
    const ps = (BOOK.pages[n].text || '').split(/\n\n+/).filter(usable).map(clean).filter(Boolean);
    ps.forEach((c, k) => {
      if (k === 0 && cut && out.length) { const a = out.pop(); out.push(a + (/[가-힣]$/.test(a) && /^[가-힣]/.test(c) ? '' : ' ') + c); }
      else out.push(c);
    });
    cut = ps.length > 0 && !/[.?!。…”’"')\]」』:]$/.test(ps[ps.length - 1]);
  }
  return out;
}
$('#src').onchange = async () => {
  $('#bookPick').hidden = $('#src').value !== 'book'; $('#ownPick').hidden = $('#src').value !== 'own';
  if ($('#src').value === 'book' && !BOOK) await loadBook($('#book').value);
};
$('#book').onchange = () => loadBook($('#book').value);
$('#speed').oninput = () => { $('#speedV').textContent = (+$('#speed').value).toFixed(2); };
$('#quality').oninput = () => { $('#qualityV').textContent = $('#quality').value; };

// ---------- 만들기 · 재생 ----------
async function ensureStyle() {
  const id = $('#voice').value; if (S.styleId === id) return;
  S.style = await loadVoiceStyle([`${HF}/voice_styles/${id}.json`]); S.styleId = id;
}
async function genLoop(run) {
  while (S.run === run && S.gen < S.items.length) {
    if (S.gen - S.play >= AHEAD) { await new Promise(r => setTimeout(r, 250)); continue; }
    const idx = S.gen, text = S.items[idx], tic = performance.now();
    try {
      const { wav, duration } = await S.tts.call(text, 'ko', S.style, +$('#quality').value, +$('#speed').value * 1.05, 0.3);
      if (S.run !== run) return;
      const len = Math.floor(S.tts.sampleRate * duration[0]);
      const url = URL.createObjectURL(new Blob([writeWavFile(wav.slice(0, len), S.tts.sampleRate)], { type: 'audio/wav' }));
      const ms = performance.now() - tic; S.rtf.push(duration[0] / (ms / 1000));
      S.ready.set(idx, { url, dur: duration[0] });
      log(`만듦 ${idx + 1}/${S.items.length}: 소리 ${duration[0].toFixed(1)}초를 ${(ms / 1000).toFixed(1)}초에 만듦${document.hidden ? ' (화면 잠김 중)' : ''}`);
    } catch (e) { log(`만들기 오류 ${idx + 1}: ${e.message}`); S.ready.set(idx, { url: '', dur: 0 }); }
    S.gen++; stats();
    // 처음에는 2문단을 만들어 둔 뒤 시작 (곧바로 끊기지 않게)
    const need = S.done === 0 && S.play === 0 ? Math.min(2, S.items.length) : 1;
    if (S.waiting && S.gen - S.play >= need) { S.waiting = false; playCur(); }
  }
}
function playCur() {
  if (S.play >= S.items.length) { log('끝까지 읽었습니다'); stop(false); $('#now').textContent = '— 끝 —'; return; }
  const r = S.ready.get(S.play);
  if (!r) { if (!S.waiting) { S.waiting = true; S.stalls++; stats(); log(`기다림: ${S.play + 1}번째 문단을 아직 만드는 중${document.hidden ? ' (화면 잠김 중)' : ''}`); } return; }
  if (!r.url) { S.play++; playCur(); return; }
  $('#now').textContent = S.items[S.play];
  player.src = r.url; player.play().catch(e => log('재생 오류: ' + e.message));
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
}
player.onended = () => {
  const r = S.ready.get(S.play); if (r && r.url) URL.revokeObjectURL(r.url); S.ready.delete(S.play);
  S.done++; S.play++; if (document.hidden) S.hiddenLast = Date.now(); stats(); playCur();
};
function stop(byUser = true) {
  S.run++; player.pause(); player.removeAttribute('src');
  S.ready.forEach(r => r.url && URL.revokeObjectURL(r.url)); S.ready.clear(); S.waiting = false;
  $('#playBtn').disabled = !S.tts; $('#stopBtn').disabled = true;
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'none';
  if (byUser) log('멈춤');
}
$('#stopBtn').onclick = () => stop(true);
$('#playBtn').onclick = async () => {
  if (!S.tts) return;
  // 휴대폰에서 소리가 막히지 않도록, 누른 순간 재생기를 한 번 깨워 둠
  try { player.src = SILENT; player.play().catch(() => {}); } catch (e) {}
  $('#playBtn').disabled = true;
  const src = $('#src').value;
  if (src === 'book' && !BOOK) await loadBook($('#book').value);
  S.items = src === 'pali' ? PALI.slice() : src === 'own' ? $('#own').value.split(/\n\s*\n|\n/).map(clean).filter(Boolean) : chapterParas();
  if (!S.items.length) { status('읽을 글이 없습니다.', 'bad'); $('#playBtn').disabled = false; return; }
  try { await ensureStyle(); } catch (e) { status('목소리를 불러오지 못했습니다: ' + e.message, 'bad'); $('#playBtn').disabled = false; return; }
  S.gen = 0; S.play = 0; S.done = 0; S.stalls = 0; S.rtf = []; S.ready.clear(); const run = ++S.run;
  $('#stopBtn').disabled = false;
  log(`듣기 시작: 문단 ${S.items.length}개 · 목소리 ${$('#voice').value} · 빠르기 ${$('#speed').value} · 음질 ${$('#quality').value}`);
  if ('mediaSession' in navigator) {
    try { navigator.mediaSession.metadata = new MediaMetadata({ title: '인공지능 목소리 듣기 시험', artist: src === 'book' ? $('#chap').selectedOptions[0].textContent : '테라와다불교 법보시 도서관', artwork: [{ src: '/images/og.jpg', sizes: '1200x630', type: 'image/jpeg' }] }); } catch (e) {}
    try { navigator.mediaSession.setActionHandler('play', () => player.play()); navigator.mediaSession.setActionHandler('pause', () => player.pause()); } catch (e) {}
  }
  S.waiting = true; stats();
  genLoop(run);
};

// ---------- 화면 잠금 기록 ----------
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { S.hiddenAt = Date.now(); S.hiddenLast = 0; log('화면 잠김 / 다른 앱으로 이동'); }
  else if (S.hiddenAt) {
    const away = (Date.now() - S.hiddenAt) / 1000, heard = S.hiddenLast ? (S.hiddenLast - S.hiddenAt) / 1000 : 0;
    log(`화면 돌아옴: ${Math.round(away)}초 동안 떠나 있었고, 그동안 문단 끝까지 들은 마지막 때는 잠근 뒤 ${Math.round(heard)}초`);
    $('#sHidden').textContent = `${Math.round(away)}초 중 약 ${Math.round(heard)}초`;
  }
});
$('#copyLog').onclick = async () => { try { await navigator.clipboard.writeText($('#log').textContent); alert('기록을 복사했습니다. 대화창에 붙여 넣어 주세요.'); } catch (e) { alert('복사하지 못했습니다. 기록을 길게 눌러 직접 복사해 주세요.'); } };
