"""
SEO quick wins:
- Unique, <=60 char metaTitles for content pages (fix duplicates + overlength).
- Fill empty image alt text (![](...)) with the page/post title.
"""
import re
from pathlib import Path

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
BRAND = " | Autotheorieoefenen"

def split_fm(text):
    if not text.startswith("---"): return None, text
    end = text.index("\n---", 3)
    return text[3:end].strip("\n").split("\n"), text[end + 4:]
def get(fm, key):
    for l in fm:
        m = re.match(rf'^{key}:\s*(.*)$', l)
        if m: return m.group(1).strip().strip('"')
    return None
def setk(fm, key, value):
    value = value.replace('"', "'")
    line = f'{key}: "{value}"'
    for i, l in enumerate(fm):
        if re.match(rf'^{key}:', l): fm[i] = line; return
    fm.append(line)
def sentence(slug):
    s = slug.replace("-", " "); return s[:1].upper() + s[1:]
def shorten(t, n=60):
    if len(t) <= n: return t
    cut = t[:n]
    if " " in cut: cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" -|·,:!")

# ---- titles ----
page_files = sorted((ROOT / "src/content/pages").glob("*.md"), key=lambda p: p.stem)
assigned = set()
title_log = []
# first pass: record titles that stay (unique + short) so duplicates can be detected deterministically
records = []
for f in page_files:
    fm, body = split_fm(f.read_text(encoding="utf-8"))
    mt = (get(fm, "metaTitle") or get(fm, "title") or sentence(f.stem))
    records.append((f, fm, body, mt))

counts = {}
for _, _, _, mt in records: counts[mt] = counts.get(mt, 0) + 1

for f, fm, body, mt in records:
    dup = counts.get(mt, 0) > 1
    toolong = len(mt) > 62
    new = mt
    if dup:
        base = sentence(f.stem)
        new = base + BRAND if len(base + BRAND) <= 60 else base
    elif toolong:
        new = shorten(mt, 60)
    # guarantee uniqueness
    if new in assigned:
        base = sentence(f.stem)
        new = base + BRAND if len(base + BRAND) <= 60 else base
        if new in assigned: new = (base + " – info")[:62]
    assigned.add(new)
    if new != mt:
        setk(fm, "metaTitle", new)
        f.write_text("---\n" + "\n".join(fm) + "\n---\n" + body, encoding="utf-8")
        title_log.append(f"{f.name}: {mt[:45]!r} -> {new!r}")

# ---- alt text ----
EMPTY_ALT = re.compile(r"!\[\s*\]\(")
alt_count = 0
for d in ["pages", "blog"]:
    for f in (ROOT / "src/content" / d).glob("*.md"):
        fm, body = split_fm(f.read_text(encoding="utf-8"))
        if fm is None: continue
        title = (get(fm, "title") or sentence(f.stem)).replace("[", "").replace("]", "")
        if EMPTY_ALT.search(body):
            n = len(EMPTY_ALT.findall(body))
            body = EMPTY_ALT.sub(f"![{title}](", body)
            f.write_text("---\n" + "\n".join(fm) + "\n---\n" + body, encoding="utf-8")
            alt_count += n

print(f"Titels aangepast: {len(title_log)}")
for l in title_log: print("  " + l)
print(f"\nLege alt-teksten ingevuld: {alt_count}")
