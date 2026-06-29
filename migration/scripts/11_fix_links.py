"""
Fix broken internal links in migrated markdown (src/content/pages + blog).
- Normalize each internal link URL (strip domain/double-domain, trim, lowercase, spaces->hyphens, known typos).
- If the normalized target is a valid built route -> rewrite the link URL.
- If not -> unwrap the link (keep anchor text, drop the link).
Idempotent. Prints a change log.
"""
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
DIST = ROOT / "dist"
CONTENT_DIRS = [ROOT / "src" / "content" / "pages", ROOT / "src" / "content" / "blog"]

# Valid routes from the built site
VALID = set()
for p in DIST.rglob("index.html"):
    rel = p.parent.relative_to(DIST).as_posix()
    VALID.add("/" if rel == "." else f"/{rel}/")

TYPO = {
    "parkeerverbordsbord": "parkeerverbodsbord",
    "motor-theorie-oefenen": "motor-theorie",
}
DOMAINS = ("https://autotheorieoefenen.com", "http://autotheorieoefenen.com",
           "https://www.autotheorieoefenen.com", "https://autotheorieoefenen.net",
           "https://theorieexamenoefenen.net")
LINK_RE = re.compile(r"(!?)\[([^\]]+)\]\(\s*([^)\s]+(?:\s[^)]*?)?)\s*\)")

def normalize(url: str):
    """Return a normalized internal path, or None if not internal."""
    u = unquote(url.strip())
    u = u.split("#")[0].split("?")[0]
    # double-domain bug: /https://domain/path  or //domain/path
    u = re.sub(r"^/+(https?:)", r"\1", u)
    for d in DOMAINS:
        if u.startswith(d):
            u = u[len(d):] or "/"
            break
    if not u.startswith("/"):
        return None
    # strip, lowercase, spaces->hyphens, collapse
    parts = [seg for seg in u.split("/") if seg.strip() != ""]
    parts = [re.sub(r"\s+", "-", seg.strip()).lower() for seg in parts]
    parts = [TYPO.get(seg, seg) for seg in parts]
    path = "/" + "/".join(parts)
    if path != "/" and not path.endswith("/"):
        path += "/"
    return path

def main():
    fixed, unwrapped, files_changed = 0, 0, 0
    log = []
    for d in CONTENT_DIRS:
        for f in d.glob("*.md"):
            text = f.read_text(encoding="utf-8")
            changed = False

            def repl(m):
                nonlocal changed, fixed, unwrapped
                bang, label, url = m.group(1), m.group(2), m.group(3)
                if bang:  # image, leave alone
                    return m.group(0)
                norm = normalize(url)
                if norm is None:  # external / mailto / tel
                    return m.group(0)
                if norm in VALID:
                    if url != norm:
                        changed = True; fixed += 1
                        log.append(f"FIX  {f.name}: {url!r} -> {norm}")
                        return f"[{label}]({norm})"
                    return m.group(0)
                # not a valid page -> unwrap (keep text)
                changed = True; unwrapped += 1
                log.append(f"UNWRAP {f.name}: {url!r} (geen pagina) -> tekst behouden")
                return label

            new = LINK_RE.sub(repl, text)
            if changed:
                f.write_text(new, encoding="utf-8")
                files_changed += 1
    print(f"Links gerepareerd: {fixed}")
    print(f"Links uitgepakt (geen doelpagina): {unwrapped}")
    print(f"Bestanden gewijzigd: {files_changed}\n")
    for l in log:
        print("  " + l)

if __name__ == "__main__":
    main()
