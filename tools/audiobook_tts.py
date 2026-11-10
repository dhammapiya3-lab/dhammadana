# 새 세션에서: pip download melotts==0.1.1 --no-deps 로 소스를 받아 풀고 MELO_SRC=그 폴더 (필요한 꾸러미는 오류를 보며 설치)
"""오디오북 원고(장별 txt) → 장별 mp3 + 문장 시간표(json)
  python3 tts_book.py 원고폴더 출력폴더 [속도]
- 문단마다 소리를 따로 만들어(조각은 cache/ 에 저장 → 멈췄다가 다시 돌려도 이어서) 이어 붙임
- 문단 사이 0.6초, 장 제목 뒤 1.2초 쉼
- times.json: 문단마다 시작·끝 초 (나중에 '듣는 문장 따라가기'에 씀)
"""
import sys, os, json, glob, hashlib, re, subprocess, time
sys.path.insert(0, os.environ.get('MELO_SRC', '/home/claude/tts/src/melotts-0.1.1'))  # MeloTTS 소스 폴더
import numpy as np, soundfile as sf
src, out = sys.argv[1], sys.argv[2]
speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
os.makedirs(out, exist_ok=True); cache = os.path.join(out, 'cache'); os.makedirs(cache, exist_ok=True)
import torch; torch.set_num_threads(2)
from melo.api import TTS
m = TTS(language='KR', device='cpu'); spk = m.hps.data.spk2id['KR']; SR = m.hps.data.sampling_rate


def safe(text):
    t = text.replace(';', ',').replace(':', ',').replace('·', ', ').replace('—', ', ').replace('–', ', ').replace('…', '. ')
    t = re.sub(r'[“”"‘’「」『』《》〈〉<>\[\]{}()（）]', ' ', t)
    t = re.sub(r'[^0-9가-힣A-Za-z.,?! ]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def say(text):
    h = hashlib.sha1(f'{speed}|{text}'.encode()).hexdigest()[:16]
    f = os.path.join(cache, h + '.wav')
    if not os.path.exists(f):
        try: m.tts_to_file(text, spk, f + '.tmp.wav', speed=speed, quiet=True)
        except Exception: m.tts_to_file(safe(text), spk, f + '.tmp.wav', speed=speed, quiet=True)
        os.replace(f + '.tmp.wav', f)
    d, sr = sf.read(f)
    return d


files = sorted(glob.glob(os.path.join(src, '*.txt')))
total = sum(len(open(f, encoding='utf-8').read()) for f in files); done = 0; t0 = time.time()
for f in files:
    name = os.path.splitext(os.path.basename(f))[0]
    mp3 = os.path.join(out, name + '.mp3')
    paras = [p.strip() for p in open(f, encoding='utf-8').read().split('\n\n') if p.strip()]
    if os.path.exists(mp3):
        done += sum(len(p) for p in paras); continue
    times, pos = [], 0.0
    wav = os.path.join(out, name + '.wav')
    with sf.SoundFile(wav, 'w', samplerate=SR, channels=1, subtype='PCM_16') as wf:  # 조각마다 바로 파일에 써서 메모리를 아낌
        for k, p in enumerate(paras):
            line = re.sub(r'\s*\n\s*', ', ', p)  # 게송 줄 바꿈은 짧게 쉬기
            d = say(line).astype('float32')
            times.append({'k': k, 'start': round(pos, 2), 'end': round(pos + len(d) / SR, 2), 'text': p})
            gap = 1.2 if k == 0 else 0.6
            wf.write(d); wf.write(np.zeros(int(SR * gap), dtype='float32')); pos += len(d) / SR + gap
            done += len(p)
            el = time.time() - t0
            print(f'\r{name[:20]} {k+1}/{len(paras)}  전체 {done*100//total}%  {el/60:.0f}분 지남', end='', flush=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-ac', '1', '-b:a', '64k', mp3 + '.tmp.mp3'], check=True)
    os.replace(mp3 + '.tmp.mp3', mp3); os.remove(wav)
    json.dump(times, open(os.path.join(out, name + '.times.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'\n✓ {name}.mp3  {pos/60:.1f}분')
print('끝', f'{(time.time()-t0)/60:.0f}분')
