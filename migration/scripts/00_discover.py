"""
Discovery pass over the WordPress export for autotheorieoefenen.com blog.
Lists categories with counts, post URL structure, post-type counts, and a
sample of post titles/slugs so we can configure the spam filter correctly
BEFORE converting. Read-only; writes a summary to migration/source/.
"""
import json
import re
from collections import Counter
from pathlib import Path
from lxml import etree as ET

NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}
ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
SOURCE = ROOT / "migration" / "source" / "wp-export.xml"
OUT = ROOT / "migration" / "source"

def text(elem, tag, ns=None):
    f = elem.find(tag, ns) if ns else elem.find(tag)
    return (f.text or "").strip() if f is not None else ""

def main():
    parser = ET.XMLParser(recover=True, huge_tree=True)
    channel = ET.parse(str(SOURCE), parser).getroot().find("channel")

    type_counts = Counter()
    status_counts = Counter()
    cat_counts = Counter()           # nicename -> count (posts only, published)
    cat_names = {}                   # nicename -> display name
    sample_links = []
    posts = []

    for item in channel.findall("item"):
        pt = text(item, "wp:post_type", NS)
        type_counts[pt] += 1
        if pt != "post":
            continue
        st = text(item, "wp:status", NS)
        status_counts[st] += 1
        if st != "publish":
            continue
        slug = text(item, "wp:post_name", NS)
        title = text(item, "title")
        link = text(item, "link")
        date = text(item, "wp:post_date", NS)[:10]
        cats = []
        for c in item.findall("category"):
            if c.get("domain") == "category":
                nn = c.get("nicename", "")
                cats.append(nn)
                cat_counts[nn] += 1
                cat_names[nn] = (c.text or "").strip()
        posts.append({"slug": slug, "title": title, "link": link, "date": date, "cats": cats})
        if len(sample_links) < 15 and link:
            sample_links.append(link)

    lines = []
    lines.append("=== POST TYPES ===")
    for t, n in type_counts.most_common():
        lines.append(f"  {n:>5}  {t}")
    lines.append("")
    lines.append("=== POST STATUS (post only) ===")
    for s, n in status_counts.most_common():
        lines.append(f"  {n:>5}  {s}")
    lines.append("")
    lines.append(f"=== CATEGORIES ({len(cat_counts)} total) ===")
    for nn, n in cat_counts.most_common():
        lines.append(f"  {n:>5}  {nn}   ({cat_names.get(nn,'')})")
    lines.append("")
    lines.append("=== SAMPLE POST LINKS (URL structure) ===")
    for l in sample_links:
        lines.append(f"  {l}")
    lines.append("")
    lines.append("=== SAMPLE TITLES (first 40, newest-ish order in file) ===")
    for p in posts[:40]:
        lines.append(f"  [{p['date']}] {p['slug']}  | {p['title'][:70]}")

    report = "\n".join(lines)
    (OUT / "discover_report.txt").write_text(report, encoding="utf-8")
    (OUT / "discover_posts.json").write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(report)

if __name__ == "__main__":
    main()
