"""
Convert snelslagen.nl WordPress XML export to Astro markdown.
- Blog posts -> src/content/blog/
- SEO pages  -> src/content/pages/  (WooCommerce system pages skipped)
- Products   -> printed to stdout for reference
"""
import html as htmllib
import json
import re
import sys
from pathlib import Path

try:
    from lxml import etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

try:
    from markdownify import markdownify
    HAS_MD = True
except ImportError:
    HAS_MD = False
    print("WARNING: markdownify not installed, content will be raw HTML", file=sys.stderr)

NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
}

ROOT = Path(__file__).parent.parent
XML_PATH = Path(r"C:\Users\Jeroen\Downloads\snelslagen.WordPress.2026-06-29.xml")
OUT_BLOG = ROOT / "src" / "content" / "blog"
OUT_PAGES = ROOT / "src" / "content" / "pages"

OUT_BLOG.mkdir(parents=True, exist_ok=True)
OUT_PAGES.mkdir(parents=True, exist_ok=True)

# WooCommerce and system pages that we build ourselves
SKIP_PAGE_SLUGS = {
    "winkel", "winkelwagen", "afrekenen", "mijn-account", "mijn-account-2",
    "home", "sitemap", "resultaten-bekijken", "quiz", "quiz-start", "quiz-einde",
    "proefexamen", "verlanglijstje", "order-received", "bestelling-voltooid",
    "checkout", "sample-page", "privacy-policy", "algemene-voorwaarden-2",
    "over-ons-2", "contact-2", "succes",
}

META_DESC_KEYS = ["_yoast_wpseo_metadesc", "_rank_math_description", "_seopress_titles_desc"]
META_TITLE_KEYS = ["_yoast_wpseo_title", "_rank_math_title", "_seopress_titles_title"]

IMG_RE = re.compile(
    r"https?://(?:www\.)?snelslagen\.nl/(?:[^/]+/)*wp-content/uploads/([^\s\"')<]+)",
    re.I,
)
LINK_RE = re.compile(r'href="https?://(?:www\.)?snelslagen\.nl(/[^"]*)?(?:#[^"]*)?"|href="https?://snelslagen\.nl"', re.I)
H1_RE = re.compile(r"^\s*<h1[^>]*>.*?</h1>\s*", re.I | re.S)
EM_DASH_RE = re.compile(r"\s*—\s*")


def text(elem, tag, ns=None):
    f = elem.find(tag, ns) if ns else elem.find(tag)
    return (f.text or "").strip() if f is not None else ""


def yq(s):
    if s is None:
        return '""'
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()
    return f'"{s}"'


def postmeta(item):
    m = {}
    for pm in item.findall("wp:postmeta", NS):
        m[text(pm, "wp:meta_key", NS)] = text(pm, "wp:meta_value", NS)
    return m


def rewrite_body(body, slug, manifest):
    if not body:
        return ""
    body = H1_RE.sub("", body, count=1)

    def img_replace(m):
        path = m.group(1).split("?")[0]
        fn = path.rsplit("/", 1)[-1]
        manifest.append({
            "source_url": f"https://snelslagen.nl/wp-content/uploads/{path}",
            "local_path": f"public/assets/images/blog/{slug}/{fn}",
            "slug": slug,
        })
        return f"/assets/images/blog/{slug}/{fn}"

    body = IMG_RE.sub(img_replace, body)
    body = re.sub(r'\s*srcset="[^"]*"', "", body)
    body = re.sub(r'\s*sizes="[^"]*"', "", body)
    body = LINK_RE.sub(lambda m: f'href="{m.group(1) or "/"}"', body)
    # YouTube iframes: keep as-is (MDX supports HTML)
    return body


def to_md(body):
    if not HAS_MD:
        return body
    md = markdownify(body, heading_style="ATX", bullets="-", strip=["script", "style"])
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = EM_DASH_RE.sub(": ", md)
    return "\n".join(ln.rstrip() for ln in md.splitlines()).strip() + "\n"


def clean_text(s):
    return EM_DASH_RE.sub(": ", htmllib.unescape(s)).strip()


def write_md(out_dir, slug, fm, body_md):
    lines = ["---"]
    for k, v in fm.items():
        if v == "" or v is None:
            continue
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, list):
            if not v:
                continue
            lines.append(f"{k}:")
            lines += [f"  - {yq(x)}" for x in v]
        else:
            lines.append(f"{k}: {yq(v)}")
    lines.append("---\n")
    (out_dir / f"{slug}.md").write_text("\n".join(lines) + "\n" + body_md, encoding="utf-8")


def main():
    if not XML_PATH.exists():
        sys.exit(f"ERROR: XML not found at {XML_PATH}")

    try:
        parser = ET.XMLParser(recover=True, huge_tree=True)
        channel = ET.parse(str(XML_PATH), parser).getroot().find("channel")
    except TypeError:
        import xml.etree.ElementTree as StdET
        channel = StdET.parse(str(XML_PATH)).getroot().find("channel")

    manifest = []
    blog_written = []
    page_written = []
    products = []
    warnings = []

    for item in channel.findall("item"):
        post_type = text(item, "wp:post_type", NS)
        status = text(item, "wp:status", NS)
        slug = text(item, "wp:post_name", NS)

        if not slug or status != "publish":
            continue

        title = clean_text(text(item, "title"))
        date = text(item, "wp:post_date", NS)
        ce = item.find("content:encoded", NS)
        raw_content = ce.text if ce is not None and ce.text else ""
        ee = item.find("excerpt:encoded", NS)
        excerpt = clean_text(ee.text or "") if ee is not None else ""

        cats = [(c.text or "").strip() for c in item.findall("category") if c.get("domain") == "category"]
        tags = [(c.text or "").strip() for c in item.findall("category") if c.get("domain") == "post_tag"]
        meta = postmeta(item)

        mdesc = clean_text(next((meta[k] for k in META_DESC_KEYS if meta.get(k)), ""))
        mtitle = clean_text(next((meta[k] for k in META_TITLE_KEYS if meta.get(k)), ""))

        if post_type == "product":
            price = meta.get("_price", "") or meta.get("_regular_price", "")
            products.append({"title": title, "slug": slug, "price": price})
            continue

        cleaned = rewrite_body(raw_content, slug, manifest)
        body_md = to_md(cleaned) if cleaned else ""

        # Auto-generate description if missing
        if not mdesc and body_md:
            for ln in body_md.splitlines():
                ln = ln.strip()
                if not ln or ln[0] in "#![|>-":
                    continue
                plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", ln)
                plain = re.sub(r"[*_`]+", "", plain)
                mdesc = (plain[:152].rsplit(" ", 1)[0] + "...") if len(plain) > 155 else plain
                break

        if post_type == "post":
            fm = {
                "title": title,
                "slug": slug,
                "date": date.split(" ")[0] if date else "",
                "metaTitle": mtitle or title,
                "metaDescription": mdesc,
                "categories": cats or ["Blog"],
                "tags": tags,
                "excerpt": excerpt,
                "homepageSafe": True,
                "draft": False,
            }
            write_md(OUT_BLOG, slug, fm, body_md)
            blog_written.append(slug)

        elif post_type == "page":
            if slug in SKIP_PAGE_SLUGS:
                continue
            fm = {
                "title": title,
                "slug": slug,
                "metaTitle": mtitle or title,
                "metaDescription": mdesc,
            }
            write_md(OUT_PAGES, slug, fm, body_md)
            page_written.append(slug)

    # Save manifest and products
    (ROOT / "migration" / "images_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (ROOT / "migration" / "products.json").write_text(
        json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Blog posts written : {len(blog_written)}")
    print(f"Pages written      : {len(page_written)}")
    print(f"Products found     : {len(products)}")
    print(f"Image refs         : {len(manifest)}")
    if warnings:
        print(f"Warnings           : {len(warnings)}")
    if products:
        print("\nProducts:")
        for p in products:
            print(f"  {p['title']} — slug: {p['slug']} — price: {p['price']}")


if __name__ == "__main__":
    main()
