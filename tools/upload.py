#!/usr/bin/env python3
"""tools/out/ 안의 파일을 Cloudflare R2(files.dhammadana.kr)에 올립니다.

처음 한 번: tools/.env 파일을 만들고 아래 네 줄을 채웁니다. (이 파일은 GitHub에 올라가지 않습니다)
  R2_ACCOUNT_ID=...
  R2_ACCESS_KEY_ID=...
  R2_SECRET_ACCESS_KEY=...
  R2_BUCKET=dhammadana-files

쓰는 법:
  python3 tools/upload.py            # tools/out 전체 올리기 (이미 같은 크기로 있는 파일은 건너뜀)
  python3 tools/upload.py --dry-run  # 무엇을 올릴지만 보기
필요한 것: pip install boto3
"""
import argparse, mimetypes, os, sys
import boto3

HERE = os.path.dirname(os.path.abspath(__file__))
env = {}
p = os.path.join(HERE, '.env')
if not os.path.exists(p): sys.exit('tools/.env 파일이 없습니다. 이 파일 맨 위 설명을 보세요.')
for line in open(p, encoding='utf-8'):
    if '=' in line and not line.strip().startswith('#'):
        k, v = line.strip().split('=', 1); env[k.strip()] = v.strip()
ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--src', default=os.path.join(HERE, 'out'))
a = ap.parse_args()
s3 = boto3.client('s3', endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                  aws_access_key_id=env['R2_ACCESS_KEY_ID'], aws_secret_access_key=env['R2_SECRET_ACCESS_KEY'], region_name='auto')
B = env['R2_BUCKET']
mimetypes.add_type('image/webp', '.webp'); mimetypes.add_type('application/epub+zip', '.epub')
n = skip = 0
for root, _, files in os.walk(a.src):
    for f in files:
        full = os.path.join(root, f); key = os.path.relpath(full, a.src).replace(os.sep, '/')
        size = os.path.getsize(full)
        try:
            if s3.head_object(Bucket=B, Key=key)['ContentLength'] == size and not key.endswith('manifest.json'):
                skip += 1; continue
        except Exception: pass
        ct = mimetypes.guess_type(f)[0] or 'application/octet-stream'
        if ct.startswith('application/json'): ct = 'application/json; charset=utf-8'
        print(('(보기만) ' if a.dry_run else '') + key)
        if not a.dry_run:
            s3.upload_file(full, B, key, ExtraArgs={'ContentType': ct, 'CacheControl': 'public, max-age=86400' if key.endswith('.json') else 'public, max-age=31536000'})
        n += 1
print(f'올림 {n}개, 이미 있어 건너뜀 {skip}개')
