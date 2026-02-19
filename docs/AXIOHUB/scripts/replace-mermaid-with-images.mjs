#!/usr/bin/env node
/**
 * replace-mermaid-with-images.mjs
 *
 * Copies source markdown files to build/md-with-images/,
 * replacing ```mermaid...``` blocks with image references
 * pointing to the pre-rendered PNG diagrams.
 *
 * Usage: node scripts/replace-mermaid-with-images.mjs
 */

import { readFile, writeFile, mkdir, copyFile, readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const BUILD = join(ROOT, 'build');
const MD_OUT = join(BUILD, 'md-with-images');

// All 6 source files with their language and diagram status
const SOURCE_FILES = [
  { file: 'AXIOHUB-ARCHITECTURE-DIAGRAMS.md', lang: 'en', hasDiagrams: true },
  { file: 'AXIOHUB-PRODUCT-DOCUMENTATION.md', lang: 'en', hasDiagrams: true },
  { file: 'AXIOHUB-API-REFERENCE.md', lang: 'en', hasDiagrams: false },
  { file: 'AXIOHUB-MIMARI-DIYAGRAMLAR.md', lang: 'tr', hasDiagrams: true },
  { file: 'AXIOHUB-URUN-DOKUMANTASYONU.md', lang: 'tr', hasDiagrams: true },
  { file: 'AXIOHUB-API-REFERANSI.md', lang: 'tr', hasDiagrams: false },
];

/**
 * Slugify heading — must match extract-mermaid.mjs logic exactly.
 */
function slugify(heading) {
  const numMatch = heading.match(/^(\d+)\.\s*/);
  const num = numMatch ? numMatch[1].padStart(2, '0') : '';
  const rest = numMatch ? heading.slice(numMatch[0].length) : heading;

  const slug = rest
    .toLowerCase()
    .replace(/[&]/g, '')
    .replace(/[^a-z0-9şçğıöüâ]+/g, '-')
    .replace(/^-|-$/g, '');

  return num ? `${num}-${slug}` : slug;
}

/**
 * Replace mermaid code blocks with image references.
 * Uses relative paths from md-with-images/ to diagrams/{lang}/.
 */
function replaceMermaidBlocks(content, lang) {
  const lines = content.split('\n');
  const output = [];
  let currentHeading = 'untitled';
  let inMermaid = false;
  let blockIndex = 0;

  for (const line of lines) {
    const headingMatch = line.match(/^##\s+(.+)/);
    if (headingMatch) {
      currentHeading = headingMatch[1].trim();
    }

    if (line.trim() === '```mermaid') {
      inMermaid = true;
      blockIndex++;
      const slug = slugify(currentHeading) || `diagram-${blockIndex}`;
      const imgPath = `diagrams/${lang}/${slug}.png`;

      // Replace the mermaid block with an image reference
      output.push(`![${currentHeading}](${imgPath})`);
      output.push('');
      continue;
    }

    if (inMermaid && line.trim() === '```') {
      inMermaid = false;
      continue;
    }

    if (inMermaid) {
      // Skip mermaid code lines
      continue;
    }

    output.push(line);
  }

  return output.join('\n');
}

// ── Main ──

async function main() {
  console.log('╔══════════════════════════════════════════╗');
  console.log('║  Replacing Mermaid Blocks with Images    ║');
  console.log('╚══════════════════════════════════════════╝\n');

  await mkdir(MD_OUT, { recursive: true });

  // Copy diagram PNGs into md-with-images/diagrams/ so md-to-pdf can serve them
  for (const lang of ['en', 'tr']) {
    const srcDir = join(BUILD, 'diagrams', lang);
    const destDir = join(MD_OUT, 'diagrams', lang);
    await mkdir(destDir, { recursive: true });

    if (existsSync(srcDir)) {
      const files = await readdir(srcDir);
      const pngs = files.filter(f => f.endsWith('.png'));
      for (const png of pngs) {
        await copyFile(join(srcDir, png), join(destDir, png));
      }
      console.log(`📋 Copied ${pngs.length} PNGs to md-with-images/diagrams/${lang}/`);
    }
  }
  console.log('');

  for (const { file, lang, hasDiagrams } of SOURCE_FILES) {
    const srcPath = join(ROOT, file);
    const destPath = join(MD_OUT, file);

    if (!existsSync(srcPath)) {
      console.warn(`⚠ File not found: ${file}`);
      continue;
    }

    if (!hasDiagrams) {
      // API reference — no diagrams, just copy as-is
      await copyFile(srcPath, destPath);
      console.log(`📋 ${file} → copied (no diagrams)`);
      continue;
    }

    const content = await readFile(srcPath, 'utf-8');
    const replaced = replaceMermaidBlocks(content, lang);
    await writeFile(destPath, replaced, 'utf-8');

    const blockCount = (content.match(/```mermaid/g) || []).length;
    console.log(`📄 ${file} → ${blockCount} blocks replaced with images`);
  }

  console.log('\n═══ All markdown files processed ═══');
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
