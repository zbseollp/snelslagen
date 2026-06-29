"""
Crawl the main (Laravel) site autotheorieoefenen.com.
- BFS from homepage + known routes, same-domain only.
- Skips blog/quiz/auth/exams/system + asset files.
- Extracts title, meta description, h1, and the main content block -> markdown.
- Rewrites internal links to relative; collects image URLs to a manifest.
Outputs: migration/source/live/<slug>.html (raw), migration/output/pages/<slug>.md,
         migration/output/pages_index.json, migration/output/page_images_manifest.json
"""
import html as htmllib
import json
import re
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from lxml import html as LH
from markdownify import markdownify

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
LIVE = ROOT / "migration" / "source" / "live"
OUTP = ROOT / "migration" / "output" / "pages"
LIVE.mkdir(parents=True, exist_ok=True); OUTP.mkdir(parents=True, exist_ok=True)

BASE = "https://autotheorieoefenen.com"
H = {"User-Agent": "Mozilla/5.0 (migration-bot)"}
SKIP_PREFIX = ("/blog", "/quiz", "/auth", "/exams", "/lead", "/links",
               "/start_mailing", "/gogosupercrawler", "/css", "/js", "/img",
               "/assets", "/fonts", "/storage", "/vendor")
SKIP_EXT = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".css", ".js",
            ".ico", ".pdf", ".xml", ".zip", ".woff", ".woff2", ".mp4")
_FIXED = ["/", "/over-ons", "/contact", "/alle-verkeersborden", "/verkeersborden-oefenen",
          "/theorie-examen-oefenen", "/rijscholen-overzicht", "/motor-theorie"]
# Candidate topic slugs (network template; non-existent ones simply 404)
_TOPICS = """afbuigende-voorrangsweg afrijden-cbr alleborden anwb-theorie auto-theorie-cursus-amsterdam
auto-theorie-ezelsbruggetje auto-theorieboek bandenspanning-autotheorie bord-niet-parkeren cbr-slagingspercentage
cbr-theorie-examen-vragen cbr-uitslag dagcursus-auto-theorie dronken-op-de-fiets faalangst-rijexamen fietspad-bord
gelijkwaardig-kruispunt gevaarherkenning-oefenen groene-streep-op-de-weg haaientanden herexamen-cbr
hoe-lang-is-je-auto-theorie-geldig hoeveel-fouten-theorie-examen-auto informatie internationaal-rijbewijs
kosten-theorie-examen-auto matrixborden militaire-colonne motor-theorie-tips niet-parkeren-bord nieuwe-verkeersborden
onderborden onverharde-wegen parkeerverbodsbord reactiesnelheid-berekenen remweg-berekenen rijbewijs-a rijbewijs-b
rijexamen rvv-verkeersborden scooter-theorie slipcursus snelheid-met-aanhanger snelweg-bord soorten-verkeersborden
symbolen-auto taxi-theorie theorie theorie-examen-auto-aanvragen theorie-examen-cursus theorie-examen-oefenen-arabisch
theorie-examen-oefenen-engels theorie-examen-oefenen-turks theorie-examen-tips theorie-in-1-dag theorie-snel-halen
trekgewicht-auto vaarbewijs-1 vaarbewijs-2 vaarbewijs-examen vaarbewijs-theorie vergelijk verkeersborden
verkeersborden-fiets verkeersborden-kopen verkeersborden-oefenen-uitleg verkeersborden-parkeren
verkeersborden-verboden-in-te-rijden verkeersborden-voorrang verkeersregelaar voorrangsregels
wanneer-hebben-voetgangers-voorrang wat-is-dimlicht""".split()
SEEDS = _FIXED + [f"/{s}" for s in _TOPICS]
CHROME_CLASSES = ("navbar", "banner", "bg-white", "footer", "header")
CAP = 300

def norm(path):
    path = path.split("#")[0].split("?")[0]
    if not path.startswith("/"):
        return None
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return path or "/"

def skip(path):
    if path is None: return True
    if any(path.startswith(p) for p in SKIP_PREFIX): return True
    if any(path.lower().endswith(e) for e in SKIP_EXT): return True
    return False

def slugify(path):
    return "home" if path == "/" else path.strip("/").replace("/", "__")

def main_content(doc):
    body = doc.find(".//body")
    best, best_len = None, 0
    if body is None: return None
    for child in body.iterchildren():
        if not isinstance(child.tag, str) or child.tag in ("script", "style", "nav", "header", "footer"):
            continue
        cls = child.get("class", "") or ""
        if any(c in cls for c in CHROME_CLASSES):
            continue
        L = len(child.text_content())
        if L > best_len:
            best_len, best = L, child
    return best

IMG_HOSTS = {}
def extract(path, text, manifest):
    doc = LH.fromstring(text)
    title = (doc.findtext(".//title") or "").strip()
    mdesc = ""
    for m in doc.xpath("//meta[@name='description']"):
        mdesc = (m.get("content") or "").strip(); break
    h1 = ""
    h1s = doc.xpath("//h1")
    if h1s: h1 = " ".join(h1s[0].text_content().split())
    node = main_content(doc)
    if node is None:
        return title, mdesc, h1, ""
    # strip first h1 inside content (dup of title)
    for h in node.xpath(".//h1")[:1]:
        h.getparent().remove(h)
    # rewrite links + images
    slug = slugify(path)
    for a in node.xpath(".//a[@href]"):
        href = a.get("href")
        if href.startswith(BASE):
            a.set("href", href[len(BASE):] or "/")
    for img in node.xpath(".//img[@src]"):
        src = urljoin(BASE + path, img.get("src"))
        host = urlparse(src).netloc; IMG_HOSTS[host] = IMG_HOSTS.get(host, 0) + 1
        fn = urlparse(src).path.rsplit("/", 1)[-1] or "img"
        manifest.append({"source_url": src, "local_path": f"public/assets/images/pages/{slug}/{fn}", "slug": slug, "filename": fn})
        img.set("src", f"/assets/images/pages/{slug}/{fn}")
        img.attrib.pop("srcset", None); img.attrib.pop("sizes", None)
    inner = LH.tostring(node, encoding="unicode")
    md = markdownify(inner, heading_style="ATX", bullets="-", strip=["script", "style"])
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = "\n".join(l.rstrip() for l in md.splitlines()).strip() + "\n"
    return title, mdesc, h1, md

def yq(s):
    s = str(s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()
    return f'"{s}"'

def main():
    seen, queue, index, manifest, thin = set(), deque(), [], [], []
    for s in SEEDS: queue.append(s)
    while queue and len(seen) < CAP:
        path = norm(queue.popleft())
        if path is None or path in seen or skip(path): continue
        seen.add(path)
        try:
            r = requests.get(BASE + path, headers=H, timeout=20)
        except Exception as e:
            index.append({"path": path, "status": "ERR", "error": str(e)[:80]}); continue
        if r.status_code != 200:
            index.append({"path": path, "status": r.status_code}); continue
        slug = slugify(path)
        (LIVE / f"{slug}.html").write_text(r.text, encoding="utf-8")
        title, mdesc, h1, md = extract(path, r.text, manifest)
        # discover links
        doc = LH.fromstring(r.text)
        for a in doc.xpath("//a[@href]"):
            href = a.get("href", "")
            if href.startswith(BASE): href = href[len(BASE):]
            if href.startswith("/"):
                np = norm(href)
                if np and np not in seen and not skip(np):
                    queue.append(np)
        # write page md
        if len(md) < 200:
            thin.append(path)
        fm = ["---", f"title: {yq(title)}", f"slug: {yq(slug)}", f"metaTitle: {yq(title)}",
              f"metaDescription: {yq(mdesc)}", f"sourceUrl: {yq(BASE + path)}", "---\n"]
        (OUTP / f"{slug}.md").write_text("\n".join(fm) + "\n" + md, encoding="utf-8")
        index.append({"path": path, "slug": slug, "status": 200, "title": title,
                      "metaDescription": mdesc, "content_chars": len(md), "h1": h1})

    (ROOT / "migration" / "output" / "pages_index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    (ROOT / "migration" / "output" / "page_images_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    ok = [i for i in index if i.get("status") == 200]
    print(f"Pages crawled (200): {len(ok)}")
    print(f"Non-200 / errors: {len([i for i in index if i.get('status') != 200])}")
    print(f"Thin content (<200 chars): {len(thin)} -> {thin[:15]}")
    print(f"Image refs: {len(manifest)}  hosts: {IMG_HOSTS}")
    print(f"Sample pages:")
    for i in ok[:12]:
        print(f"  /{i['slug']}  [{i['content_chars']}c]  {i['title'][:60]}")

if __name__ == "__main__":
    main()
