"""
Full on-page/technical SEO audit over the built site (dist/).
Checks per page: title (len/dup), meta description (len/dup), H1 count,
canonical, OG/Twitter, JSON-LD, lang, word count (thin), images missing alt,
heading-order skips, internal/external link counts.
Prints a prioritized summary + writes migration/output/seo_audit.json.
"""
import json, re
from collections import Counter, defaultdict
from pathlib import Path
from lxml import html as LH

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
DIST = ROOT / "dist"

def route_of(p):
    rel = p.parent.relative_to(DIST).as_posix()
    return "/" if rel == "." else f"/{rel}/"

pages = []
titles = defaultdict(list)
descs = defaultdict(list)

for p in DIST.rglob("index.html"):
    route = route_of(p)
    doc = LH.fromstring(p.read_text(encoding="utf-8", errors="ignore"))
    title = (doc.findtext(".//title") or "").strip()
    desc = ""
    for m in doc.xpath("//meta[@name='description']"):
        desc = (m.get("content") or "").strip(); break
    canonical = bool(doc.xpath("//link[@rel='canonical']"))
    og = len(doc.xpath("//meta[starts-with(@property,'og:')]"))
    tw = len(doc.xpath("//meta[starts-with(@name,'twitter:')]"))
    jsonld = len(doc.xpath("//script[@type='application/ld+json']"))
    htmllang = doc.xpath("//html/@lang")
    h1s = doc.xpath("//main//h1") or doc.xpath("//h1")
    main = doc.xpath("//main")
    main_el = main[0] if main else doc
    text = " ".join(main_el.text_content().split())
    words = len(text.split())
    imgs = main_el.xpath(".//img")
    imgs_no_alt = sum(1 for i in imgs if not (i.get("alt") or "").strip())
    # heading order skip detection
    heads = [int(h.tag[1]) for h in main_el.xpath(".//h1|.//h2|.//h3|.//h4|.//h5|.//h6")]
    skip = any(heads[i] - heads[i-1] > 1 for i in range(1, len(heads)))
    int_links = len([a for a in main_el.xpath(".//a[@href]") if (a.get("href") or "").startswith(("/", "https://autotheorieoefenen.com"))])
    ext_links = len([a for a in main_el.xpath(".//a[@href]") if (a.get("href") or "").startswith("http") and "autotheorieoefenen.com" not in (a.get("href") or "")])

    rec = {"route": route, "title": title, "title_len": len(title), "desc": desc, "desc_len": len(desc),
           "canonical": canonical, "og": og, "twitter": tw, "jsonld": jsonld, "lang": htmllang[0] if htmllang else "",
           "h1": len(h1s), "words": words, "imgs": len(imgs), "imgs_no_alt": imgs_no_alt,
           "heading_skip": skip, "int_links": int_links, "ext_links": ext_links}
    pages.append(rec)
    if title: titles[title].append(route)
    if desc: descs[desc].append(route)

def filt(pred): return [p["route"] for p in pages if pred(p)]

issues = {
    "missing_title": filt(lambda p: not p["title"]),
    "title_too_long(>62)": filt(lambda p: p["title_len"] > 62),
    "title_too_short(<25)": filt(lambda p: 0 < p["title_len"] < 25),
    "duplicate_titles": {t: r for t, r in titles.items() if len(r) > 1},
    "missing_desc": filt(lambda p: not p["desc"]),
    "desc_too_long(>165)": filt(lambda p: p["desc_len"] > 165),
    "desc_too_short(<70)": filt(lambda p: 0 < p["desc_len"] < 70),
    "duplicate_desc": {d[:50]: r for d, r in descs.items() if len(r) > 1},
    "no_h1": filt(lambda p: p["h1"] == 0),
    "multiple_h1": filt(lambda p: p["h1"] > 1),
    "no_canonical": filt(lambda p: not p["canonical"]),
    "no_jsonld": filt(lambda p: p["jsonld"] == 0),
    "thin_content(<300w)": filt(lambda p: p["words"] < 300),
    "images_missing_alt": {p["route"]: p["imgs_no_alt"] for p in pages if p["imgs_no_alt"] > 0},
    "heading_order_skips": filt(lambda p: p["heading_skip"]),
    "low_internal_links(<3)": filt(lambda p: p["int_links"] < 3),
}

# infra checks
robots = (DIST / "robots.txt").exists()
sitemap = (DIST / "sitemap-index.xml").exists()
headers = (DIST / "_headers").exists()
redirects = (DIST / "_redirects").exists()

out = {"pages_total": len(pages), "infra": {"robots.txt": robots, "sitemap-index.xml": sitemap, "_headers": headers, "_redirects": redirects},
       "issues": issues}
(ROOT / "migration" / "output" / "seo_audit.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Pages analysed: {len(pages)}")
print(f"Infra: robots={robots} sitemap={sitemap} _headers={headers} _redirects={redirects}")
print("\n--- ISSUE COUNTS ---")
for k, v in issues.items():
    n = len(v) if isinstance(v, (list, dict)) else v
    print(f"  {n:>4}  {k}")
print("\n--- DETAILS (samples) ---")
for k in ["missing_title","missing_desc","title_too_long(>62)","desc_too_short(<70)","desc_too_long(>165)","multiple_h1","no_h1","thin_content(<300w)","low_internal_links(<3)"]:
    v = issues[k]
    if v: print(f"\n{k} ({len(v)}):"); [print("   ", x) for x in (v[:12] if isinstance(v,list) else list(v)[:12])]
print(f"\nduplicate_titles: {len(issues['duplicate_titles'])}")
for t, r in list(issues["duplicate_titles"].items())[:8]:
    print(f"   {len(r)}x  {t[:70]!r}  -> {r[:3]}")
print(f"\nduplicate_desc groups: {len(issues['duplicate_desc'])}")
print(f"images_missing_alt pages: {len(issues['images_missing_alt'])}  (total imgs w/o alt: {sum(issues['images_missing_alt'].values())})")
