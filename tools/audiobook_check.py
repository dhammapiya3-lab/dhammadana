"""오디오북 검수: 문단 소리 조각을 음성 인식(whisper)으로 받아 적어 원고와 비교
  python3 asr_check.py 원고폴더 캐시폴더 [all|risky] > 결과
"""
import sys, os, re, glob, json, hashlib, random, difflib
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
from faster_whisper import WhisperModel
import soundfile as sf, numpy as np
from scipy.signal import resample_poly
from math import gcd
def load(f):
    d, sr = sf.read(f, dtype='float32')
    if d.ndim > 1: d = d.mean(1)
    g = gcd(sr, 16000); return resample_poly(d, 16000 // g, sr // g).astype('float32')
src, cache, mode = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else 'risky')
m = WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4)
RISK = re.compile(r'[^가-힣\s.,?!]')
han = lambda s: re.sub(r'[^가-힣]', '', s)
items = []
for f in sorted(glob.glob(os.path.join(src, '*.txt'))):
    name = os.path.basename(f)[:-4]
    for k, p in enumerate([p.strip() for p in open(f, encoding='utf-8').read().split('\n\n') if p.strip()]):
        line = re.sub(r'\s*\n\s*', ', ', p)
        h = hashlib.sha1(f'1.0|{line}'.encode()).hexdigest()[:16]
        items.append((name, k, p, os.path.join(cache, h + '.wav')))
random.seed(1)
pick = [x for x in items if RISK.search(x[2])] if mode == 'risky' else items
if mode == 'risky' and len(items) > 200: pick += random.sample([x for x in items if not RISK.search(x[2]) and len(x[2]) > 30], 30)
out = []
for name, k, p, wav in pick:
    if not os.path.exists(wav): print(json.dumps({'name': name, 'k': k, 'missing': True}, ensure_ascii=False), flush=True); continue
    segs, _ = m.transcribe(load(wav), language='ko', beam_size=1, vad_filter=False)
    heard = ' '.join(s.text.strip() for s in segs)
    r = difflib.SequenceMatcher(None, han(p), han(heard)).ratio()
    print(json.dumps({'name': name, 'k': k, 'ratio': round(r, 3), 'text': p[:300], 'heard': heard[:300]}, ensure_ascii=False), flush=True)
