"""
SEO defect fixes on markdown frontmatter:
- blog: metaTitle containing '%%' (unresolved Yoast var) -> real title
- pages: empty title -> sentence-cased slug; empty metaTitle -> title (+brand if it fits);
         empty metaDescription -> first body paragraph (~155 chars)
"""
import re
from pathlib import Path

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
BRAND = " | Autotheorieoefenen"

def split_fm(text):
    if not text.startswith("---"):
        return None, text
    end = text.index("\n---", 3)
    return text[3:end].strip("\n").split("\n"), text[end + 4:]

def get(fm, key):
    for l in fm:
        m = re.match(rf'^{key}:\s*(.*)$', l)
        if m:
            return m.group(1).strip().strip('"')
    return None

def setk(fm, key, value):
    value = value.replace('"', "'")
    line = f'{key}: "{value}"'
    for i, l in enumerate(fm):
        if re.match(rf'^{key}:', l):
            fm[i] = line; return
    fm.append(line)

def titleize(slug):
    s = slug.replace("-", " ")
    return s[:1].upper() + s[1:]

def first_para(body):
    for ln in body.split("\n"):
        ln = ln.strip()
        if not ln or ln[0] in "#!>|" or ln.startswith("["):
            continue
        ln = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', ln)
        ln = re.sub(r'[*_`#]+', '', ln).strip()
        if len(ln) > 40:
            if len(ln) > 155:
                ln = ln[:155].rsplit(" ", 1)[0] + "..."
            return ln
    return ""

log = []

# blog: fix %%title%%
for f in (ROOT / "src/content/blog").glob("*.md"):
    text = f.read_text(encoding="utf-8")
    fm, body = split_fm(text)
    if fm is None: continue
    mt = get(fm, "metaTitle") or ""
    if "%" in mt:
        title = get(fm, "title") or titleize(f.stem)
        setk(fm, "metaTitle", title)
        f.write_text("---\n" + "\n".join(fm) + "\n---\n" + body, encoding="utf-8")
        log.append(f"BLOG metaTitle fix: {f.name}")

# pages: fill empty title/metaTitle/metaDescription
for f in (ROOT / "src/content/pages").glob("*.md"):
    text = f.read_text(encoding="utf-8")
    fm, body = split_fm(text)
    if fm is None: continue
    changed = False
    title = get(fm, "title") or ""
    if not title:
        title = titleize(f.stem); setk(fm, "title", title); changed = True
        log.append(f"PAGE title: {f.name} -> {title!r}")
    mt = get(fm, "metaTitle") or ""
    if not mt or "%" in mt:
        mt = (title + BRAND) if len(title + BRAND) <= 62 else title
        setk(fm, "metaTitle", mt); changed = True
    md = get(fm, "metaDescription") or ""
    if not md:
        d = first_para(body)
        if d:
            setk(fm, "metaDescription", d); changed = True
            log.append(f"PAGE desc: {f.name} -> {d[:60]!r}")
    if changed:
        f.write_text("---\n" + "\n".join(fm) + "\n---\n" + body, encoding="utf-8")

print(f"Changes: {len(log)}")
for l in log: print("  " + l)
