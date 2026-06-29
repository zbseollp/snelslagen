"""Probe the HTML structure of the live site so we can write the extractor."""
import requests
from lxml import html as LH

H = {"User-Agent": "Mozilla/5.0 (migration-bot)"}
for url in ["https://autotheorieoefenen.com/", "https://autotheorieoefenen.com/voorrangsregels"]:
    print("=" * 70)
    print("URL:", url)
    r = requests.get(url, headers=H, timeout=20)
    print("status:", r.status_code, "len:", len(r.text))
    doc = LH.fromstring(r.text)
    # head meta
    t = doc.findtext(".//title")
    print("title:", (t or "").strip()[:120])
    for m in doc.xpath("//meta[@name='description'] | //meta[@property='og:title'] | //meta[@property='og:description'] | //link[@rel='canonical']"):
        key = m.get("name") or m.get("property") or m.get("rel")
        val = m.get("content") or m.get("href")
        print(f"  meta {key}: {(val or '')[:120]}")
    # structural containers
    for tag in ["main", "article", "section"]:
        els = doc.xpath(f"//{tag}")
        if els:
            print(f"  <{tag}> count: {len(els)}; first class='{els[0].get('class','')}'")
    # top-level body children with classes
    body = doc.find(".//body")
    if body is not None:
        print("  body direct children:")
        for c in body.iterchildren():
            if isinstance(c.tag, str):
                txt = " ".join(c.text_content().split())[:50]
                print(f"    <{c.tag} class='{c.get('class','')}' id='{c.get('id','')}'>  ~{len(c.text_content())} chars  :: {txt}")
    print("h1:", [" ".join(h.text_content().split())[:80] for h in doc.xpath('//h1')][:3])
