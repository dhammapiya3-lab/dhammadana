"""'글로 보기'용 글 모으기 (운영자 요청, 2026-11-15): 한글 그림이 있는 이야기마다 쪽별로 그림 속 한국어 글을
읽는 순서(위→아래, 같은 줄이면 왼쪽→오른쪽)로 모아 <사이트>/storybooks/data/texts.json 에 씀. 작은 이름표(label)는 뺌.
python3 pipeline/texts.py <사이트 폴더>"""
import json, sys
SITE = sys.argv[1]
READY = json.load(open("data/rendered.json"))
out = {}
for key in sorted(READY):
    try: pages = json.load(open(f"ko/{key}.json", encoding="utf-8"))
    except FileNotFoundError: continue
    res = []
    for p in pages[:READY[key]]:
        items = []
        for b in p.get("boxes", []):
            if not isinstance(b, dict): continue
            t = (b.get("ko") or "").strip()
            if not t or b.get("label"): continue
            def first(v):  # [x,y,…] 또는 [[x,y,…],…]
                while isinstance(v, list) and v and isinstance(v[0], list): v = v[0]
                return (v[0], v[1]) if isinstance(v, list) and len(v) >= 2 else (0, 0)
            x, y = first(b.get("rect") or b.get("seed") or b.get("parts") or [])
            items.append((x, y, t))
        items.sort(key=lambda a: (a[1], a[0]))
        rows = []  # 같은 높이(±30)는 왼쪽부터
        for it in items:
            if rows and abs(rows[-1][0][1] - it[1]) <= 30: rows[-1].append(it)
            else: rows.append([it])
        seen, lines = set(), []
        for r in rows:
            for x, y, t in sorted(r):
                if t not in seen: seen.add(t); lines.append(t)
        res.append(lines)
    out[key] = res
json.dump(out, open(f"{SITE}/storybooks/data/texts.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
print("글로 보기:", len(out), "이야기")
