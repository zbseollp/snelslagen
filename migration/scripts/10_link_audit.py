"""
Link audit over the built site (dist/).
- Valid routes = every dist/**/index.html (+ 404).
- Redirect sources parsed from public/_redirects (so redirected links aren't 'broken').
- Broken internal links: root-relative <a href> whose target is not a valid route,
  not a redirect source, not an asset/file, not external.
- Orphan pages: built pages with 0 inbound links from OTHER pages' <main> content
  AND not present in the global header/footer navigation.
Outputs migration/output/link_audit.json + prints a summary.
"""
import json, re
from pathlib import Path
from lxml import html as LH

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
DIST = ROOT / "dist"
REDIRECTS = ROOT / "public" / "_redirects"
ASSET_RE = re.compile(r"\.(png|jpe?g|gif|svg|webp|ico|css|js|xml|txt|pdf|woff2?|mp4|json)$", re.I)

def norm(path: str) -> str:
    path = path.split("#")[0].split("?")[0]
    if not path.startswith("/"):
        return ""
    if path != "/" and not path.endswith("/"):
        path += "/"
    return path

def is_internal(href: str) -> str | None:
    if not href: return None
    for dom in ("https://autotheorieoefenen.com", "http://autotheorieoefenen.com",
                "https://www.autotheorieoefenen.com", "https://autotheorieoefenen.net",
                "https://theorieexamenoefenen.net"):
        if href.startswith(dom):
            href = href[len(dom):] or "/"
            break
    if href.startswith("/"):
        return href
    return None  # external / mailto / tel / anchor

# 1. valid routes
valid = set()
for p in DIST.rglob("index.html"):
    rel = p.parent.relative_to(DIST).as_posix()
    valid.add("/" if rel == "." else f"/{rel}/")
valid.add("/404/")

# 2. redirect sources (handle wildcards)
redirect_prefixes, redirect_exact = [], set()
if REDIRECTS.exists():
    for line in REDIRECTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        src = line.split()[0]
        if src.endswith("*"): redirect_prefixes.append(src[:-1])
        else: redirect_exact.add(norm(src))

def covered_by_redirect(path: str) -> bool:
    if path in redirect_exact or path.rstrip("/") in {s.rstrip('/') for s in redirect_exact}: return True
    return any(path.startswith(pre) for pre in redirect_prefixes)

# 3. parse all pages
all_links = []          # (source_route, target_path, in_main)
inbound_main = {}       # target -> set(source) from <main>
global_nav = set()      # links in header/footer (present site-wide)
page_routes = []

for p in DIST.rglob("index.html"):
    rel = p.parent.relative_to(DIST).as_posix()
    route = "/" if rel == "." else f"/{rel}/"
    page_routes.append(route)
    doc = LH.fromstring(p.read_text(encoding="utf-8", errors="ignore"))
    main = doc.xpath("//main")
    main_el = main[0] if main else None
    main_hrefs = set()
    if main_el is not None:
        for a in main_el.xpath(".//a[@href]"):
            ip = is_internal(a.get("href"))
            if ip is not None: main_hrefs.add(norm(ip) or ip)
    for a in doc.xpath("//header//a[@href] | //footer//a[@href]"):
        ip = is_internal(a.get("href"))
        if ip is not None: global_nav.add(norm(ip) or ip)
    for a in doc.xpath(".//a[@href]"):
        ip = is_internal(a.get("href"))
        if ip is None: continue
        t = norm(ip) or ip
        all_links.append((route, t))
    for t in main_hrefs:
        if t != route:
            inbound_main.setdefault(t, set()).add(route)

# 4. broken internal links (dedup by (source,target))
broken = {}
for src, tgt in set(all_links):
    if ASSET_RE.search(tgt): continue
    if tgt in valid: continue
    if covered_by_redirect(tgt): continue
    broken.setdefault(tgt, []).append(src)

# 5. orphans: built content pages with 0 inbound-main links and not in global nav
SKIP = {"/404/", "/contact/thanks/"}
orphans = []
for route in sorted(page_routes):
    if route in SKIP: continue
    if route in global_nav: continue
    if len(inbound_main.get(route, set())) == 0:
        orphans.append(route)

report = {
    "valid_routes": len(valid),
    "broken_targets": {k: sorted(set(v)) for k, v in sorted(broken.items())},
    "broken_count": len(broken),
    "orphans": orphans,
    "orphan_count": len(orphans),
}
(ROOT / "migration" / "output" / "link_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Valid routes: {len(valid)}")
print(f"\nBROKEN internal link targets: {len(broken)}")
for tgt, srcs in sorted(broken.items()):
    print(f"  {tgt}   <- linked from {len(srcs)} page(s) e.g. {srcs[0]}")
print(f"\nORPHAN pages (0 inbound content links, not in nav/footer): {len(orphans)}")
for o in orphans:
    print(f"  {o}")
