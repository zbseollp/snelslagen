"""Build attachment ID -> {url, alt, filename} map from the WP export."""
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from lxml import etree as ET

NS = {"wp": "http://wordpress.org/export/1.2/", "content": "http://purl.org/rss/1.0/modules/content/", "dc": "http://purl.org/dc/elements/1.1/"}
ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
SOURCE = ROOT / "migration" / "source" / "wp-export.xml"
OUT = ROOT / "migration" / "source" / "attachments.json"

def text(elem, tag, ns=None):
    f = elem.find(tag, ns) if ns else elem.find(tag)
    return (f.text or "").strip() if f is not None else ""

def main():
    parser = ET.XMLParser(recover=True, huge_tree=True)
    channel = ET.parse(str(SOURCE), parser).getroot().find("channel")
    attachments = {}
    hosts = Counter()
    for item in channel.findall("item"):
        if text(item, "wp:post_type", NS) != "attachment":
            continue
        pid = text(item, "wp:post_id", NS)
        url = text(item, "wp:attachment_url", NS)
        alt = ""
        for pm in item.findall("wp:postmeta", NS):
            if text(pm, "wp:meta_key", NS) == "_wp_attachment_image_alt":
                alt = text(pm, "wp:meta_value", NS)
        attachments[pid] = {"url": url, "alt": alt, "filename": url.rsplit("/", 1)[-1] if url else ""}
        if url:
            hosts[urlparse(url).netloc] += 1
    OUT.write_text(json.dumps(attachments, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(attachments)} attachments")
    print("Image hosts:", dict(hosts))
    print("Sample URLs:")
    for k, v in list(attachments.items())[:8]:
        print(f"  {v['url']}  (alt='{v['alt'][:40]}')")

if __name__ == "__main__":
    main()
