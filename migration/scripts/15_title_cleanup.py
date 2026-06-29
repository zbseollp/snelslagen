"""Strip dangling trailing words/symbols from shortened metaTitles."""
import re
from pathlib import Path
ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
DANGLING = {"en","van","voor","de","het","naar","met","om","te","of","in","op","uw","je","wat","moet","tot","bij","over","als"}

def split_fm(text):
    if not text.startswith("---"): return None, text
    end = text.index("\n---", 3)
    return text[3:end].strip("\n").split("\n"), text[end+4:]

log = []
for f in (ROOT/"src/content/pages").glob("*.md"):
    fm, body = split_fm(f.read_text(encoding="utf-8"))
    if fm is None: continue
    changed = False
    for i, l in enumerate(fm):
        m = re.match(r'^metaTitle:\s*"(.*)"\s*$', l)
        if not m: continue
        t = m.group(1); orig = t
        for _ in range(3):
            t = t.rstrip()
            t2 = re.sub(r'[\s|:,\-–&]+$', '', t)            # trailing separators/symbols
            t2 = re.sub(r'\s+(\w+)$', lambda mm: '' if mm.group(1).lower() in DANGLING else mm.group(0), t2)
            if t2 == t: t = t2; break
            t = t2
        t = t.strip()
        if t and t != orig:
            fm[i] = f'metaTitle: "{t}"'; changed = True; log.append(f"{f.name}: {orig!r} -> {t!r}")
    if changed:
        f.write_text("---\n"+"\n".join(fm)+"\n---\n"+body, encoding="utf-8")
print(f"Opgeschoond: {len(log)}")
for l in log: print("  "+l)
