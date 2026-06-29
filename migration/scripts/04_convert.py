"""
Convert ALL 78 published blog posts to markdown with frontmatter.
- Keeps every published post (SEO value preserved).
- Tags off-topic/celebrity posts with homepageSafe: false (from blog_drop.json)
  so they resolve at /blog/<slug>/ but stay off the homepage.
- Rewrites .net/.com/blog image + link URLs to local/relative paths.
Outputs to migration/output/ for review before moving into the Astro project (Phase 2).
"""
import html as htmllib
import json
import re
from pathlib import Path
from lxml import etree as ET
from markdownify import markdownify

NS = {"wp": "http://wordpress.org/export/1.2/", "content": "http://purl.org/rss/1.0/modules/content/",
      "dc": "http://purl.org/dc/elements/1.1/", "excerpt": "http://wordpress.org/export/1.2/excerpt/"}
ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
SOURCE = ROOT / "migration" / "source" / "wp-export.xml"
ATTACH = ROOT / "migration" / "source" / "attachments.json"
DROP = ROOT / "migration" / "source" / "blog_drop.json"
OUT = ROOT / "migration" / "output"

# Match image uploads on either domain, with or without /blog prefix
IMG_RE = re.compile(r"https?://autotheorieoefenen\.(?:net|com)/blog/wp-content/uploads/([^\s\"')]+)", re.I)
# Internal links to either domain -> strip to path
LINK_RE = re.compile(r'href="https?://autotheorieoefenen\.(?:net|com)(/[^"]*)?"', re.I)
H1_RE = re.compile(r"^\s*<h1[^>]*>.*?</h1>\s*", re.I | re.S)

META_TITLE_KEYS = ["_yoast_wpseo_title", "_rank_math_title", "_seopress_titles_title", "rank_math_title"]
META_DESC_KEYS = ["_yoast_wpseo_metadesc", "_rank_math_description", "_seopress_titles_desc", "rank_math_description"]

def text(elem, tag, ns=None):
    f = elem.find(tag, ns) if ns else elem.find(tag)
    return (f.text or "").strip() if f is not None else ""

def yq(s):
    if s is None: return '""'
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()
    return f'"{s}"'

def postmeta(item):
    m = {}
    for pm in item.findall("wp:postmeta", NS):
        m[text(pm, "wp:meta_key", NS)] = text(pm, "wp:meta_value", NS)
    return m

def old_slugs(item):
    return [text(pm, "wp:meta_value", NS) for pm in item.findall("wp:postmeta", NS)
            if text(pm, "wp:meta_key", NS) == "_wp_old_slug" and text(pm, "wp:meta_value", NS)]

def rewrite(body, slug, manifest, warnings):
    if not body: return ""
    body = H1_RE.sub("", body, count=1)
    def img(m):
        path = m.group(1).split("?")[0]
        fn = path.rsplit("/", 1)[-1]
        manifest.append({"source_url": f"https://autotheorieoefenen.net/blog/wp-content/uploads/{path}",
                         "local_path": f"public/assets/images/blog/{slug}/{fn}", "slug": slug, "filename": fn})
        return f"/assets/images/blog/{slug}/{fn}"
    body = IMG_RE.sub(img, body)
    body = re.sub(r'\s*srcset="[^"]*"', "", body)
    body = re.sub(r'\s*sizes="[^"]*"', "", body)
    body = LINK_RE.sub(lambda m: f'href="{m.group(1) or "/"}"', body)
    if "wp-content" in body: warnings.append(f"{slug}: wp-content leftover")
    if "autotheorieoefenen.net" in body or "autotheorieoefenen.com" in body: warnings.append(f"{slug}: old-domain leftover")
    return body

def to_md(body):
    md = markdownify(body, heading_style="ATX", bullets="-", strip=["script", "style"])
    md = re.sub(r"\n{3,}", "\n\n", md)
    return "\n".join(l.rstrip() for l in md.splitlines()).strip() + "\n"

def main():
    attach = json.loads(ATTACH.read_text(encoding="utf-8"))
    drop_slugs = {p["slug"] for p in json.loads(DROP.read_text(encoding="utf-8"))}
    parser = ET.XMLParser(recover=True, huge_tree=True)
    channel = ET.parse(str(SOURCE), parser).getroot().find("channel")
    out_blog = OUT / "blog"; out_blog.mkdir(parents=True, exist_ok=True)
    manifest, warnings, redirects, written = [], [], [], []

    for item in channel.findall("item"):
        if text(item, "wp:post_type", NS) != "post" or text(item, "wp:status", NS) != "publish":
            continue
        slug = text(item, "wp:post_name", NS)
        title = text(item, "title")
        date = text(item, "wp:post_date", NS)
        author = text(item, "dc:creator", NS)
        ce = item.find("content:encoded", NS)
        content = ce.text if ce is not None and ce.text else ""
        ee = item.find("excerpt:encoded", NS)
        excerpt = ee.text if ee is not None and ee.text else ""
        cats = [(c.text or "").strip() for c in item.findall("category") if c.get("domain") == "category"]
        tags = [(c.text or "").strip() for c in item.findall("category") if c.get("domain") == "post_tag"]
        meta = postmeta(item)

        featured, falt = "", ""
        tid = meta.get("_thumbnail_id", "")
        if tid and tid in attach and attach[tid]["filename"]:
            fn = attach[tid]["filename"]
            featured = f"/assets/images/blog/{slug}/{fn}"
            falt = attach[tid]["alt"] or title
            manifest.append({"source_url": attach[tid]["url"], "local_path": f"public/assets/images/blog/{slug}/{fn}",
                             "slug": slug, "filename": fn, "featured": True})

        cleaned = rewrite(content, slug, manifest, warnings)
        body_md = to_md(cleaned) if cleaned else ""

        mtitle = next((htmllib.unescape(meta[k]) for k in META_TITLE_KEYS if meta.get(k)), "")
        mdesc = next((htmllib.unescape(meta[k]) for k in META_DESC_KEYS if meta.get(k)), "")
        if not mdesc and body_md:
            for ln in body_md.splitlines():
                ln = ln.strip()
                if not ln or ln[0] in "#![|>-": continue
                plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", ln)
                plain = re.sub(r"[*_`]+", "", plain)
                mdesc = (plain[:152].rsplit(" ", 1)[0] + "...") if len(plain) > 155 else plain
                warnings.append(f"{slug}: meta description auto-generated")
                break
        if not mtitle:
            warnings.append(f"{slug}: no SEO-plugin meta title (using post title)")

        fm = {"title": title, "slug": slug, "date": date.split(" ")[0] if date else "",
              "author": author, "metaTitle": mtitle or title, "metaDescription": mdesc,
              "categories": cats or ["Blog"], "tags": tags, "featuredImage": featured,
              "featuredImageAlt": falt, "excerpt": htmllib.unescape((excerpt or "").strip()),
              "homepageSafe": slug not in drop_slugs, "draft": False}

        lines = ["---"]
        for k, v in fm.items():
            if v == "" or v is None: continue
            if isinstance(v, bool): lines.append(f"{k}: {'true' if v else 'false'}")
            elif isinstance(v, list):
                if not v: continue
                lines.append(f"{k}:"); lines += [f"  - {yq(x)}" for x in v]
            else: lines.append(f"{k}: {yq(v)}")
        lines.append("---\n")
        (out_blog / f"{slug}.md").write_text("\n".join(lines) + "\n" + body_md, encoding="utf-8")
        written.append(slug)
        for os in old_slugs(item):
            redirects.append(f"/blog/{os}/  /blog/{slug}/  301")

    (OUT / "images_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "redirect_map.txt").write_text("\n".join(redirects) + "\n", encoding="utf-8")
    (OUT / "_warnings.txt").write_text("\n".join(warnings) + "\n", encoding="utf-8")
    safe = sum(1 for s in written if s not in drop_slugs)
    print(f"Posts written: {len(written)}  (homepageSafe: {safe}, hidden: {len(written)-safe})")
    print(f"Unique images: {len({m['source_url'] for m in manifest})} | refs: {len(manifest)}")
    print(f"Old-slug redirects: {len(redirects)} | Warnings: {len(warnings)}")

if __name__ == "__main__":
    main()
