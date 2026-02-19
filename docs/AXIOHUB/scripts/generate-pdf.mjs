#!/usr/bin/env node
/**
 * generate-pdf.mjs
 *
 * Custom PDF generator using marked + puppeteer.
 * Embeds diagram PNGs as base64 data URIs so Puppeteer can render them
 * without needing file:// access (which setContent blocks).
 *
 * Usage: node scripts/generate-pdf.mjs
 */

import { readFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { marked } from 'marked';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const BUILD = join(ROOT, 'build');
const MD_DIR = join(BUILD, 'md-with-images');
const PDF_DIR = join(BUILD, 'pdf');
const CSS_PATH = join(__dirname, 'pdf-style.css');

const FILES = [
  { md: 'AXIOHUB-ARCHITECTURE-DIAGRAMS.md', pdf: 'AXIOHUB-ARCHITECTURE-DIAGRAMS.pdf' },
  { md: 'AXIOHUB-PRODUCT-DOCUMENTATION.md', pdf: 'AXIOHUB-PRODUCT-DOCUMENTATION.pdf' },
  { md: 'AXIOHUB-API-REFERENCE.md', pdf: 'AXIOHUB-API-REFERENCE.pdf' },
  { md: 'AXIOHUB-MIMARI-DIYAGRAMLAR.md', pdf: 'AXIOHUB-MIMARI-DIYAGRAMLAR.pdf' },
  { md: 'AXIOHUB-URUN-DOKUMANTASYONU.md', pdf: 'AXIOHUB-URUN-DOKUMANTASYONU.pdf' },
  { md: 'AXIOHUB-API-REFERANSI.md', pdf: 'AXIOHUB-API-REFERANSI.pdf' },
];

/**
 * Embed images as base64 data URIs in the HTML.
 * This avoids Puppeteer's file:// access restrictions.
 */
async function embedImages(html, baseDir) {
  const imgRegex = /src="([^"]+\.png)"/g;
  const matches = [...html.matchAll(imgRegex)];

  for (const match of matches) {
    const src = match[1];
    if (src.startsWith('http') || src.startsWith('data:')) continue;

    // Decode URL-encoded characters (marked encodes Turkish ü→%C3%BC, etc.)
    const decodedSrc = decodeURIComponent(src);
    const absPath = resolve(baseDir, decodedSrc);
    if (existsSync(absPath)) {
      const imgBuffer = await readFile(absPath);
      const base64 = imgBuffer.toString('base64');
      const dataUri = `data:image/png;base64,${base64}`;
      html = html.replaceAll(match[0], `src="${dataUri}"`);
    }
  }

  return html;
}

async function main() {
  console.log('╔══════════════════════════════════════════╗');
  console.log('║  Generating PDFs                         ║');
  console.log('╚══════════════════════════════════════════╝\n');

  await mkdir(PDF_DIR, { recursive: true });

  const css = await readFile(CSS_PATH, 'utf-8');

  const puppeteer = await import('puppeteer');
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    for (const { md, pdf } of FILES) {
      const mdPath = join(MD_DIR, md);
      if (!existsSync(mdPath)) {
        console.warn(`  ⚠ Not found: ${md}`);
        continue;
      }

      console.log(`  ⏳ ${pdf}...`);

      const markdown = await readFile(mdPath, 'utf-8');
      let html = await marked(markdown);

      // Embed PNGs as base64 data URIs
      html = await embedImages(html, MD_DIR);

      const fullHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>${css}</style>
</head>
<body>
  ${html}
</body>
</html>`;

      const page = await browser.newPage();
      try {
        await page.setContent(fullHtml, {
          waitUntil: 'networkidle0',
          timeout: 60000,
        });

        await page.pdf({
          path: join(PDF_DIR, pdf),
          format: 'A4',
          margin: { top: '20mm', bottom: '20mm', left: '18mm', right: '18mm' },
          printBackground: true,
        });

        console.log(`  ✓ ${pdf}`);
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }

  console.log('\n═══ All PDFs generated ═══');
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
