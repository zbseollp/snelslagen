"""
Extract the traffic-sign bank from the crawled /alle-verkeersborden HTML:
per sign -> {id, name, image, category}. This is the data source for the
verkeersborden quiz + the signs overview page.
"""
import json, re
from pathlib import Path
from lxml import html as LH

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
SRC = ROOT / "migration" / "source" / "live" / "alle-verkeersborden.html"
OUT = ROOT / "migration" / "output"

def main():
    doc = LH.fromstring(SRC.read_text(encoding="utf-8"))
    signs = []
    current_cat = ""
    # Walk the document in order; track latest heading as category, collect sign imgs
    body = doc.find(".//body")
    for el in body.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag in ("h1", "h2", "h3", "h4"):
            txt = " ".join(el.text_content().split())
            if txt:
                current_cat = txt
        if el.tag == "img":
            src = el.get("src", "")
            m = re.search(r"/img/borden/(\d+)\.png", src)
            if m:
                name = (el.get("title") or el.get("alt") or "").strip()
                if name.lower() == "bord":
                    name = (el.get("alt") or "").strip()
                signs.append({
                    "id": m.group(1),
                    "name": name,
                    "image": f"/assets/images/signs/{m.group(1)}.png",
                    "source_image": f"https://autotheorieoefenen.com/img/borden/{m.group(1)}.png",
                    "category": current_cat,
                })
    # de-dup by id (keep first)
    seen, uniq = set(), []
    for s in signs:
        if s["id"] in seen: continue
        seen.add(s["id"]); uniq.append(s)
    (OUT / "signs.json").write_text(json.dumps(uniq, indent=2, ensure_ascii=False), encoding="utf-8")
    cats = {}
    for s in uniq:
        cats[s["category"]] = cats.get(s["category"], 0) + 1
    print(f"Signs extracted: {len(uniq)}")
    print("By category section:")
    for c, n in cats.items():
        print(f"  {n:>3}  {c[:50]}")
    print("\nSample:")
    for s in uniq[:6]:
        print(f"  {s['id']}  {s['name'][:40]}  [{s['category'][:25]}]")

if __name__ == "__main__":
    main()
