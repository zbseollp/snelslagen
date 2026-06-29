"""
Classify the 78 published blog posts into KEEP (on-topic: auto/theorie/rijbewijs)
vs DROP (celebrity/off-topic SEO spam), based on slug patterns. Produces lists
for human review BEFORE conversion. Nothing is deleted — just categorized.
"""
import json
import re
from pathlib import Path

ROOT = Path(r"C:\Users\Jeroen\autotheorieoefenen")
POSTS = ROOT / "migration" / "source" / "discover_posts.json"
OUT = ROOT / "migration" / "source"

# Celebrity / personal-life SEO spam: any of these as a hyphen-delimited token
CELEB_TOKENS = {
    "vriendin", "vriend", "leeftijd", "vermogen", "getrouwd", "gescheiden",
    "zwanger", "kinderen", "kind", "overleden", "lengte", "afkomst", "gezin",
    "dochter", "zoon", "moeder", "vader", "partner", "vrouw", "echtgenoot",
    "echtgenote", "ex", "relatie", "biografie", "instagram",
}
# Off-topic filler (not about driving/theory at all) - substring match
OFFTOPIC_KEYWORDS = [
    "spionage", "tracker", "soundcloud", "youtube-kanaal", "social-media",
    "volgers", "tiktok", "spotify", "muziekstreaming",
    "casino", "gokken", "crypto", "bitcoin",
]
JUNK_SLUGS = {"test"}

def classify(slug, title):
    s = slug.lower()
    tokens = set(s.split("-"))
    if s in JUNK_SLUGS:
        return ("drop", "junk/test")
    hit = tokens & CELEB_TOKENS
    if hit:
        return ("drop", f"celebrity-token:{','.join(sorted(hit))}")
    if s.startswith("wie-is-"):
        return ("drop", "celebrity:wie-is")
    for k in OFFTOPIC_KEYWORDS:
        if k in s:
            return ("drop", f"offtopic:{k}")
    return ("keep", "")

def main():
    posts = json.loads(POSTS.read_text(encoding="utf-8"))
    keep, drop = [], []
    for p in posts:
        verdict, reason = classify(p["slug"], p["title"])
        rec = {**p, "reason": reason}
        (keep if verdict == "keep" else drop).append(rec)

    (OUT / "blog_keep.json").write_text(json.dumps(keep, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "blog_drop.json").write_text(json.dumps(drop, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"TOTAL published: {len(posts)}")
    print(f"KEEP (on-topic): {len(keep)}")
    print(f"DROP (spam/off-topic): {len(drop)}")
    print("\n===== DROP LIST =====")
    for p in sorted(drop, key=lambda x: x["reason"]):
        print(f"  [{p['date']}] {p['slug']}  ({p['reason']})")
    print("\n===== KEEP LIST =====")
    for p in sorted(keep, key=lambda x: x["date"]):
        print(f"  [{p['date']}] {p['slug']}")

if __name__ == "__main__":
    main()
