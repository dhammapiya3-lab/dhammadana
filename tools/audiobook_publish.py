#!/usr/bin/env python3
"""오디오북을 사이트에 붙일 정보 파일(content/audiobooks/<ID>.json)을 만듭니다.

쓰는 법:
  node tools/audiobook_script.mjs DL-0015          # 원고 + 글 자리(.map.json)
  python3 tools/audiobook_publish.py DL-0015 /home/claude/tts/book15

- 소리 파일 폴더에는 NN_장제목.mp3 와 NN_장제목.times.json (문단마다 시작·끝 초)이 있어야 합니다.
- 원고(.txt)와 소리 문단(times.json 의 text)이 한 글자라도 다르면 멈춥니다.
- 파일 저장소 주소: audio/<ID>/NN.mp3 (운영자가 /admin/upload/ 의 '오디오북 올리기'에서 올림 → 빌드가 저장소에 파일이 다 있는지 확인하고 있으면 읽기 화면에 🎧 단추가 나타남)
"""
import glob, json, os, subprocess, sys

ID, SRC = sys.argv[1], sys.argv[2]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'tools/out/audiobook', ID)
dst = os.path.join(ROOT, 'content/audiobooks', ID + '.json')
old = json.load(open(dst)) if os.path.exists(dst) else {}
chs = []
for mp in sorted(glob.glob(os.path.join(SRC, '[0-9][0-9]_*.mp3'))):
    base = os.path.basename(mp)[:-4]
    nn = base[:2]
    tm = json.load(open(os.path.join(SRC, base + '.times.json')))
    mpath = glob.glob(os.path.join(OUT, nn + '_*.map.json'))
    if not mpath: sys.exit(f'{nn}: 원고의 글 자리 파일(.map.json)이 없습니다. audiobook_script.mjs 를 먼저 돌리세요.')
    m = json.load(open(mpath[0])); tx = open(mpath[0][:-9] + '.txt', encoding='utf-8').read().strip().split('\n\n')
    if not (len(tm) == len(tx) == len(m['map'])): sys.exit(f'{nn}: 문단 수가 다릅니다 (소리 {len(tm)} / 원고 {len(tx)} / 자리 {len(m["map"])})')
    for a, b in zip(tm, tx):
        if a['text'] != b: sys.exit(f'{nn}: 원고와 소리 문단이 다릅니다: {b[:40]}')
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp]).decode())
    sync, last = [], None
    for a, (p, s) in zip(tm, m['map']):
        if (p, s) != last: sync.append([round(a['start'], 2), p, s]); last = (p, s)
    chs.append({'n': int(nn), 'title': m['title'], 'page': m['page'], 'to': m['to'], 'file': f'audio/{ID}/{nn}.mp3',
                'dur': round(dur, 1), 'size': os.path.getsize(mp), 'sync': sync})
out = {'book': ID, **({'uploaded': old['uploaded']} if old.get('uploaded') else {}), **({'up': old['up']} if old.get('up') else {}), 'voice': '기계 음성(MeloTTS)으로 만든 오디오북', 'chapters': chs}
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump(out, open(dst, 'w'), ensure_ascii=False, separators=(',', ':'))
open(dst, 'a').write('\n')
tot = sum(c['dur'] for c in chs)
print(f'{ID}: 장 {len(chs)}개, 모두 {int(tot // 3600)}시간 {int(tot % 3600 // 60)}분, 따라가기 자리 {sum(len(c["sync"]) for c in chs)}개 → {os.path.relpath(dst, ROOT)} — 소리 파일이 저장소에 다 있으면 빌드 때 저절로 켜짐')
