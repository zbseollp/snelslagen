"""
Download blog images from the manifest into the Astro public/ folder.
- Tries the .net source URL, falls back to .com.
- If a sized variant (-1024x576) 404s, retries the base filename.
Saves to public/assets/images/blog/<slug>/<filename>.
"""
import json
import os
import re
import time
from pathlib import Path
import requests

def _ext(p):
    # Windows extended-length path prefix to bypass the 260-char MAX_PATH limit
    return "\\\\?\\" + os.path.abspath(str(p))

def write_bytes_long(dest, data):
    os.makedirs(_ext(dest.parent), exist_ok=True)
    with open(_ext(dest), "wb") as f:
        f.write(data)

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
MANIFEST = ROOT / "migration" / "output" / "images_manifest.json"
PUBLIC = ROOT / "public"
SIZE_RE = re.compile(r"-\d{2,4}x\d{2,4}(?=\.[A-Za-z0-9]+$)")
HEADERS = {"User-Agent": "Mozilla/5.0 (migration-bot)"}

def candidates(url):
    urls = [url]
    if "autotheorieoefenen.net" in url:
        urls.append(url.replace("autotheorieoefenen.net", "autotheorieoefenen.com"))
    # add size-stripped variants as fallback
    extra = []
    for u in urls:
        if SIZE_RE.search(u):
            extra.append(SIZE_RE.sub("", u))
    return urls + extra

def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    seen, ok, fail = {}, 0, []
    for m in manifest:
        dest = ROOT / m["local_path"]
        if dest.exists():
            ok += 1; continue
        src = m["source_url"]
        if src in seen and seen[src]:
            write_bytes_long(dest, seen[src]); ok += 1; continue
        data = None
        for u in candidates(src):
            try:
                r = requests.get(u, headers=HEADERS, timeout=20)
                if r.status_code == 200 and r.content and len(r.content) > 100:
                    data = r.content; break
            except Exception:
                pass
        if data:
            write_bytes_long(dest, data)
            seen[src] = data; ok += 1
        else:
            seen[src] = None; fail.append(src)
        time.sleep(0.05)
    print(f"Downloaded/exists: {ok}")
    print(f"Failed: {len(fail)}")
    for f in fail[:30]:
        print(f"  MISS {f}")

if __name__ == "__main__":
    main()
