"""
Regenerate public/_redirects for blog-at-root, staying under Cloudflare's
100-rule limit by collapsing all per-post redirects into ONE wildcard.

Order matters (first match wins):
  system paths -> specific old-slug renames -> consolidatie -> protect /blog/ index
  -> wildcard /blog/* -> /:splat
Writes UTF-8 without BOM.
"""
import re
from pathlib import Path

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
blog_ids = {p.stem for p in (ROOT / "src/content/blog").glob("*.md")}

L = []
L += ["# WordPress/legacy systeempaden",
      "/wp-admin/*        /404/   301",
      "/wp-login.php      /404/   301",
      "/blog/wp-admin/*   /blog/  301",
      "/blog/wp-login.php /blog/  301",
      "/blog/feed/        /blog/  301",
      "/blog/feed/*       /blog/  301",
      ""]
L += ["# Dode/legacy routes",
      "/quiz/             /verkeersborden-oefenen/   301",
      "/quiz              /verkeersborden-oefenen/   301",
      "/exams/*           /verkeersborden-oefenen/   301",
      "/exams             /verkeersborden-oefenen/   301",
      ""]
L += ["# Near-duplicate pagina-consolidatie",
      "/alleborden/       /alle-verkeersborden/      301",
      ""]

# Old slug renames (specifiek, MOET vóór de wildcard) -> root
old = []
rm = ROOT / "migration/output/redirect_map.txt"
if rm.exists():
    for ln in rm.read_text(encoding="utf-8").splitlines():
        parts = ln.split()
        if len(parts) >= 2 and parts[0].startswith("/blog/"):
            src, dst = parts[0], parts[1]
            m = re.match(r"^/blog/(.+)$", dst)
            if m:
                dst = "/" + m.group(1)
            # alleen echte renames (oude slug != huidige post-slug)
            slug = src[len("/blog/"):].strip("/")
            if slug not in blog_ids:
                old.append(f"{src}  {dst}  301")
if old:
    L += ["# Oude blog-slugs (renames) -> root (specifiek, vóór de wildcard)"] + old + [""]

L += ["# Consolidatie + junk (specifiek, vóór de wildcard)",
      "/blog/transport-naar-het-buitenland/  /transport-naar-het-buitenland-waar-te-beginnen/  301",
      "/blog/test/  /blog/  301",
      ""]

L += ["# Blogposts naar root. Named placeholder matcht /blog/<post>/ maar NIET de kale /blog/ (geen loop).",
      "/blog/:slug/  /:slug/  301",
      ""]

text = "\n".join(L) + "\n"
(ROOT / "public/_redirects").write_text(text, encoding="utf-8")  # geen BOM
total = sum(1 for x in L if x.strip().endswith(("301", "200")))
print(f"_redirects herschreven: {len(old)} renames + 1 wildcard. Totaal {total} regels (limiet 100).")
