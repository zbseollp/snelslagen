import { getCollection, type CollectionEntry } from "astro:content";

export type Post = CollectionEntry<"blog">;

export async function getAllPosts(): Promise<Post[]> {
  const posts = await getCollection("blog", (p) => !p.data.draft);
  return posts.sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
}

// Categorieën die NIET op de homepage (of in "gerelateerde artikelen") horen:
// behouden voor SEO, maar weggefilterd. Werkt zodra deze categorie in Payload
// aan de artikelen hangt.
export const NON_HOMEPAGE_CATEGORIES = new Set<string>([
  "Showbizz",
  "Bekende Nederlanders",
  "Celebrity",
  "Overig",
]);

// Eén plek die bepaalt of een post relevant is voor de homepage. Werkt met beide
// signalen: de boolean `homepageSafe` (repo) én een off-topic-categorie (Payload).
export function isRelevantForHomepage(p: Post): boolean {
  if (p.data.homepageSafe === false) return false;
  if (p.data.categories.some((c) => NON_HOMEPAGE_CATEGORIES.has(c))) return false;
  return true;
}

export async function getHomepagePosts(): Promise<Post[]> {
  return (await getAllPosts()).filter(isRelevantForHomepage);
}

// Toont een nette titel. Als de data per ongeluk de slug als titel bevat
// (alleen kleine letters + koppeltekens, geen spaties), maken we die leesbaar.
// Echte titels (met spaties/hoofdletters) blijven onaangetast.
export function displayTitle(p: Post): string {
  const t = (p.data.title ?? "").trim();
  const looksLikeSlug = t.length > 0 && !/\s/.test(t) && /^[a-z0-9]+(?:-[a-z0-9]+)+$/.test(t);
  const source = t && !looksLikeSlug ? t : (t || p.id);
  if (looksLikeSlug || !t) {
    return source
      .split("-")
      .map((w) => (w ? w.charAt(0).toUpperCase() + w.slice(1) : w))
      .join(" ");
  }
  return source;
}

// Verbergt de samenvatting als die leeg is of feitelijk gelijk is aan de slug/titel.
export function displayDescription(p: Post): string {
  const d = postDescription(p).trim();
  if (!d) return "";
  const norm = (s: string) => s.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
  if (norm(d) === p.id || norm(d) === norm(p.data.title ?? "")) return "";
  return d;
}

export async function getRecentPosts(n = 6): Promise<Post[]> {
  return (await getHomepagePosts()).slice(0, n);
}

export function slugifyCat(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export async function getCategories() {
  const posts = await getHomepagePosts();
  const map = new Map<string, number>();
  for (const p of posts) for (const c of p.data.categories) map.set(c, (map.get(c) ?? 0) + 1);
  return [...map.entries()].map(([name, count]) => ({ name, count, slug: slugifyCat(name) }));
}

export async function getRelatedPosts(current: Post, n = 4): Promise<Post[]> {
  const all = (await getHomepagePosts()).filter((p) => p.id !== current.id);
  const same = all.filter((p) => p.data.categories.some((c) => current.data.categories.includes(c)));
  const filler = all.filter((p) => !same.includes(p));
  return [...same, ...filler].slice(0, n);
}

export function readingMinutes(text?: string): number {
  if (!text) return 1;
  return Math.max(1, Math.ceil(text.trim().split(/\s+/).length / 200));
}

export function postDescription(p: Post): string {
  return p.data.metaDescription || p.data.description || p.data.excerpt || "";
}

export function formatDate(d: Date): string {
  return new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "long", year: "numeric" }).format(d);
}
