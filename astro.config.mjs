import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import mdx from "@astrojs/mdx";
import compress from "astro-compress";
import tailwindcss from "@tailwindcss/vite";

// Verwijder een losse afbeelding die bovenaan de body staat. De WordPress-migratie
// zette de featured image als eerste regel in de tekst; die tonen we nu als hero,
// dus hij hoeft niet nog een keer in de body te staan (voorkomt dubbele afbeelding).
function remarkStripLeadingImage() {
  return (tree) => {
    const kids = tree.children;
    if (!kids || kids.length === 0) return;
    const first = kids[0];
    const isImg = (n) => n && n.type === "image";
    const isImgParagraph = (n) =>
      n && n.type === "paragraph" && n.children?.length === 1 && isImg(n.children[0]);
    if (isImg(first) || isImgParagraph(first)) kids.shift();
  };
}

export default defineConfig({
  site: "https://snelslagen.nl",
  output: "static",
  trailingSlash: "always",
  build: { format: "directory" },
  prefetch: { prefetchAll: true, defaultStrategy: "viewport" },
  markdown: { remarkPlugins: [remarkStripLeadingImage] },
  integrations: [
    mdx(),
    sitemap({
      filter: (page) => !page.includes("/contact/thanks/") && !page.includes("/404"),
    }),
    compress({ CSS: true, HTML: true, Image: false, JavaScript: true, SVG: true }),
  ],
  vite: { plugins: [tailwindcss()] },
  server: { port: 4325 },
});
