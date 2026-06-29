import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

// Blog content comes from LOCAL markdown only (Payload CMS syncs files into the
// repo via GitHub Actions). No remote CMS fetching at build time.
const blog = defineCollection({
  loader: glob({ base: "./src/content/blog", pattern: "**/*.{md,mdx}" }),
  schema: z
    .object({
      title: z.string(),
      slug: z.string().optional(),
      // Both formats accepted: our migration uses `date`, Payload/AstroPayload uses `pubDate`
      date: z.coerce.date().optional(),
      pubDate: z.coerce.date().optional(),
      updatedDate: z.coerce.date().optional(),
      author: z.string().optional(),
      metaTitle: z.string().optional(),
      // Both formats accepted: our migration uses `metaDescription`/`excerpt`, Payload uses `description`
      metaDescription: z.string().optional(),
      description: z.string().optional(),
      excerpt: z.string().optional(),
      categories: z.array(z.string()).default([]),
      tags: z.array(z.string()).default([]),
      featuredImage: z.string().optional(),
      featuredImageAlt: z.string().optional(),
      // Payload/AstroPayload kan de afbeelding als `heroImage` publiceren (string-url
      // of een media-object met `url`). We normaliseren naar `featuredImage`.
      heroImage: z.union([z.string(), z.object({ url: z.string().optional(), alt: z.string().optional() }).passthrough()]).optional(),
      // Payload CMS schrijft custom frontmatter-velden via het Extra-veld als geneste key.
      extra: z.object({ featuredImage: z.string().optional(), featuredImageAlt: z.string().optional() }).passthrough().optional(),
      homepageSafe: z.boolean().default(true),
      draft: z.union([z.boolean(), z.string()]).transform((v) => v === true || v === "true").default(false),
    })
    // Normalize Payload (pubDate/description/heroImage/extra) and legacy (date/excerpt) into canonical fields
    .transform((d) => ({
      ...d,
      date: d.date ?? d.pubDate ?? new Date(),
      pubDate: d.pubDate ?? d.date ?? new Date(),
      description: d.description ?? d.metaDescription ?? d.excerpt ?? "",
      featuredImage:
        d.featuredImage ??
        d.extra?.featuredImage ??
        (typeof d.heroImage === "string" ? d.heroImage : d.heroImage?.url) ??
        undefined,
      featuredImageAlt: d.featuredImageAlt ?? d.extra?.featuredImageAlt,
    })),
});

// Static long-form pages (the migrated Laravel content pages)
const pages = defineCollection({
  loader: glob({ base: "./src/content/pages", pattern: "**/*.{md,mdx}" }),
  schema: z.object({
    title: z.string(),
    slug: z.string().optional(),
    metaTitle: z.string().optional(),
    metaDescription: z.string().optional(),
    sourceUrl: z.string().optional(),
  }),
});

export const collections = { blog, pages };
