"""Download main-site page images from page_images_manifest.json into public/.
Tries recorded URL, falls back across .net/.com, and strips size suffixes."""
import json, os, re, time
from pathlib import Path
import requests

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
MANIFEST = ROOT / "migration" / "output" / "page_images_manifest.json"
SIZE_RE = re.compile(r"-\d{2,4}x\d{2,4}(?=\.[A-Za-z0-9]+$)")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
     "Referer": "https://autotheorieoefenen.com/"}

def _ext(p): return "\\\\?\\" + os.path.abspath(str(p))
def write_long(dest, data):
    os.makedirs(_ext(dest.parent), exist_ok=True)
    with open(_ext(dest), "wb") as f: f.write(data)

def candidates(url):
    urls = [url]
    if "theorieexamenoefenen.net" in url:
        urls.append(url.replace("theorieexamenoefenen.net", "autotheorieoefenen.com"))
    if "autotheorieoefenen.com" in url:
        urls.append(url.replace("autotheorieoefenen.com", "theorieexamenoefenen.net"))
    extra = [SIZE_RE.sub("", u) for u in urls if SIZE_RE.search(u)]
    out, seen = [], set()
    for u in urls + extra:
        if u not in seen: seen.add(u); out.append(u)
    return out

def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cache, ok, fail = {}, 0, []
    for m in manifest:
        dest = ROOT / m["local_path"]
        if os.path.exists(_ext(dest)): ok += 1; continue
        src = m["source_url"]
        if src in cache:
            if cache[src]: write_long(dest, cache[src]); ok += 1
            else: fail.append(src)
            continue
        data = None
        for u in candidates(src):
            try:
                r = requests.get(u, headers=H, timeout=20)
                if r.status_code == 200 and len(r.content) > 100: data = r.content; break
            except Exception: pass
        cache[src] = data
        if data: write_long(dest, data); ok += 1
        else: fail.append(src)
        time.sleep(0.03)
    print(f"Downloaded/exists: {ok}")
    print(f"Failed: {len(fail)} (unique: {len(set(fail))})")
    for f in list(dict.fromkeys(fail))[:20]: print(f"  MISS {f}")

if __name__ == "__main__":
    main()
