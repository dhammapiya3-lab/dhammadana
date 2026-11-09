"""지난주와 이번 주의 원 사이트를 비교해 바뀐 것을 보고서로 남긴다.
python3 pipeline/diff.py <지난 catalog.json> <지난 assets_meta.json>
결과: reports/<날짜>.md, reports/latest.md, data/changes/<날짜>.json, data/new_stories.txt (글 상자 미리 찾을 이야기)
"""
import json, os, sys, datetime, glob

today = datetime.date.today().isoformat()
old = json.load(open(sys.argv[1], encoding="utf-8"))
new = json.load(open("data/catalog.json", encoding="utf-8"))
om = json.load(open(sys.argv[2], encoding="utf-8")) if os.path.exists(sys.argv[2]) else {}
nm = json.load(open("data/assets_meta.json", encoding="utf-8")) if os.path.exists("data/assets_meta.json") else {}

ch = {"date": today, "new_books": [], "removed_books": [], "new_stories": [], "removed_stories": [],
      "changed_text": [], "changed_images": [], "added_images": [], "removed_images": [], "needs_review": []}
translated = {p.split("/")[-2] + "/" + os.path.basename(p)[:-5] for p in glob.glob("ko/*/*.json")}

for slug, b in new["books"].items():
    if slug not in old["books"]:
        ch["new_books"].append({"book": slug, "title": b["title"], "stories": len(b["stories"])}); continue
    ob = old["books"][slug]
    for f in ("title", "intro", "summary"):
        if (ob.get(f) or "") != (b.get(f) or ""):
            ch["changed_text"].append({"book": slug, "field": f})
    for sf, st in b["stories"].items():
        sid = sf.rsplit(".", 1)[0]
        if sf not in ob["stories"]:
            ch["new_stories"].append({"book": slug, "story": sid, "title": st["title"]}); continue
        os_ = ob["stories"][sf]
        for f in ("title", "intro"):
            if (os_.get(f) or "") != (st.get(f) or ""):
                ch["changed_text"].append({"book": slug, "story": sid, "field": f})
        oi = [i["img"] for i in os_["items"] if "img" in i]; ni = [i["img"] for i in st["items"] if "img" in i]
        for x in ni:
            if x not in oi:
                ch["added_images"].append(f"{slug}/{x}")
            elif om.get(f"{slug}/{x}") and nm.get(f"{slug}/{x}") and om[f"{slug}/{x}"][0] != "error" \
                    and nm[f"{slug}/{x}"][0] != "error" and om[f"{slug}/{x}"] != nm[f"{slug}/{x}"]:
                ch["changed_images"].append(f"{slug}/{x}")
        ch["removed_images"] += [f"{slug}/{x}" for x in oi if x not in ni]
        if f"{slug}/{sid}" in translated and any(
                p.startswith(f"{slug}/") and any(p.endswith(x) for x in ni + oi)
                for p in ch["added_images"] + ch["changed_images"] + ch["removed_images"]):
            ch["needs_review"].append(f"{slug}/{sid}")
    ch["removed_stories"] += [{"book": slug, "story": s.rsplit(".", 1)[0]} for s in ob["stories"] if s not in b["stories"]]
ch["removed_books"] = [s for s in old["books"] if s not in new["books"]]
for c in ch["changed_text"]:
    if c.get("story") and f"{c['book']}/{c['story']}" in translated:
        ch["needs_review"].append(f"{c['book']}/{c['story']}")
ch["needs_review"] = sorted(set(ch["needs_review"]))

total = sum(len(v) for k, v in ch.items() if isinstance(v, list))
os.makedirs("data/changes", exist_ok=True); os.makedirs("reports", exist_ok=True)
json.dump(ch, open(f"data/changes/{today}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

L = [f"# 그림책 원 사이트 주간 점검 — {today}", ""]
if total == 0:
    L.append("지난주와 달라진 것이 없습니다.")
else:
    def sec(title, items, fmt):
        if items:
            L.append(f"## {title} ({len(items)})"); L.extend(f"- {fmt(x)}" for x in items[:60])
            if len(items) > 60: L.append(f"- … 외 {len(items) - 60}개")
            L.append("")
    sec("새 책", ch["new_books"], lambda x: f"{x['title']} (`{x['book']}`, 이야기 {x['stories']}편)")
    sec("새 이야기", ch["new_stories"], lambda x: f"{x['book']} / {x['title']} (`{x['story']}`)")
    sec("이미 번역한 이야기 중 다시 확인할 것", ch["needs_review"], lambda x: f"`{x}`")
    sec("다시 만들어진 그림", ch["changed_images"], lambda x: f"`{x}`")
    sec("새로 더해진 그림", ch["added_images"], lambda x: f"`{x}`")
    sec("빠진 그림", ch["removed_images"], lambda x: f"`{x}`")
    sec("바뀐 소개·제목 글", ch["changed_text"], lambda x: f"{x['book']}{' / ' + x['story'] if x.get('story') else ''} — {x['field']}")
    sec("없어진 이야기", ch["removed_stories"], lambda x: f"{x['book']} / {x['story']}")
    sec("없어진 책", ch["removed_books"], lambda x: f"`{x}`")
L.append(f"\n(책 {len(new['books'])}권 · 이야기 {sum(len(b['stories']) for b in new['books'].values())}편 · 그림 {sum(1 for b in new['books'].values() for s in b['stories'].values() for i in s['items'] if 'img' in i)}장)")
open(f"reports/{today}.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
open("reports/latest.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
open("data/new_stories.txt", "w").write("\n".join(f"{x['book']} {x['story']}.htm" for x in ch["new_stories"]) + "\n")
print("바뀐 것", total, "건 →", f"reports/{today}.md")
