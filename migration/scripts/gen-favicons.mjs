import sharp from "sharp";
import { readFileSync } from "fs";

const pub = "C:/Users/Jeroen/autotheorieoefenen/public";
const svg = readFileSync(pub + "/favicon.svg");

for (const size of [32, 192, 512]) {
  await sharp(svg, { density: 384 }).resize(size, size).png().toFile(`${pub}/favicon-${size}.png`);
  console.log("favicon-" + size + ".png");
}

// apple-touch-icon: full-bleed square (iOS applies its own rounded mask)
const square = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#f65900"/><path fill="#fff" fill-rule="evenodd" d="M32 13.5 51.5 50.5 H42.2 L38.7 43.6 H25.3 L21.8 50.5 H12.5 Z M32 27.4 28.1 35.1 H35.9 Z"/></svg>`;
await sharp(Buffer.from(square), { density: 384 }).resize(180, 180).png().toFile(`${pub}/apple-touch-icon.png`);
console.log("apple-touch-icon.png");
