#!/usr/bin/env node
/**
 * generate-product-slides.mjs
 *
 * Generates Marp-format markdown for product summary slide decks.
 * Extracts key content sections from the product documentation
 * and creates ~25 summary slides per language.
 *
 * Usage: node scripts/generate-product-slides.mjs
 */

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const BUILD = join(ROOT, 'build');
const SLIDES_DIR = join(BUILD, 'slides');

const SOURCES = [
  {
    file: 'AXIOHUB-PRODUCT-DOCUMENTATION.md',
    lang: 'en',
    output: 'AXIOHUB-PRODUCT-SUMMARY.md',
    title: 'AxioHub',
    subtitle: 'Product Overview & Architecture',
    date: 'February 2026',
  },
  {
    file: 'AXIOHUB-URUN-DOKUMANTASYONU.md',
    lang: 'tr',
    output: 'AXIOHUB-URUN-OZETI.md',
    title: 'AxioHub',
    subtitle: 'Ürün Genel Bakış ve Mimari',
    date: 'Şubat 2026',
  },
];

/**
 * Slugify — must match extract-mermaid.mjs exactly.
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
 * Parse the product documentation into sections.
 * Each section has: heading, content (text), bullets, tables, diagramSlug.
 */
function parseSections(content) {
  const sections = [];
  const lines = content.split('\n');
  let current = null;
  let inMermaid = false;
  let inTable = false;
  let tableLines = [];
  let currentH2 = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // H2 section boundary
    const h2Match = line.match(/^## (.+)/);
    if (h2Match) {
      if (current) sections.push(current);
      currentH2 = h2Match[1].trim();
      current = {
        heading: currentH2,
        slug: slugify(currentH2),
        content: [],
        bullets: [],
        tables: [],
        diagrams: [],
        subheadings: [],
      };
      continue;
    }

    if (!current) continue;

    // H3 subheading
    const h3Match = line.match(/^### (.+)/);
    if (h3Match) {
      current.subheadings.push(h3Match[1].trim());
    }

    // Mermaid block — track diagram slug
    if (line.trim() === '```mermaid') {
      inMermaid = true;
      current.diagrams.push(slugify(currentH2));
      continue;
    }
    if (inMermaid) {
      if (line.trim() === '```') inMermaid = false;
      continue;
    }

    // Table detection
    if (line.trim().startsWith('|') && line.includes('|')) {
      if (!inTable) {
        inTable = true;
        tableLines = [];
      }
      tableLines.push(line);
      continue;
    } else if (inTable) {
      inTable = false;
      if (tableLines.length > 2) {
        current.tables.push(tableLines.join('\n'));
      }
      tableLines = [];
    }

    // Bullet points
    if (line.match(/^- \*\*.+\*\*/)) {
      current.bullets.push(line);
      continue;
    }

    // Regular content (non-empty, non-separator)
    if (line.trim() && !line.startsWith('---') && !line.startsWith('>') && !line.startsWith('```')) {
      current.content.push(line.trim());
    }
  }

  if (current) sections.push(current);
  return sections;
}

/**
 * Build Marp slides from parsed sections.
 */
function buildProductSlides(sections, lang, config) {
  const relDiagramsDir = `../diagrams/${lang}`;
  const slides = [];

  // Front matter
  slides.push('---');
  slides.push('marp: true');
  slides.push('theme: default');
  slides.push('paginate: true');
  slides.push('size: 16:9');
  slides.push('style: |');
  slides.push('  section { font-family: Inter, -apple-system, sans-serif; }');
  slides.push('  section.title { display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; background: linear-gradient(135deg, #1a1a2e 0%, #2d3561 100%); color: white; }');
  slides.push('  section.title h1 { font-size: 56px; border: none; color: white; }');
  slides.push('  section.title h2 { font-size: 28px; font-weight: 400; color: #94a3b8; border: none; }');
  slides.push('  section.title p { color: #94a3b8; }');
  slides.push('  section.section-title { display: flex; flex-direction: column; justify-content: center; background: #f8fafc; }');
  slides.push('  section.section-title h1 { font-size: 40px; color: #2563eb; border-bottom: 3px solid #2563eb; }');
  slides.push('  section.diagram { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding: 40px 50px 30px; }');
  slides.push('  section.diagram h2 { font-size: 26px; color: #1a1a2e; border-bottom: 2px solid #2563eb; width: 100%; padding-bottom: 8px; margin: 0 0 12px 0; flex-shrink: 0; }');
  slides.push('  section.diagram p { display: flex; justify-content: center; align-items: center; flex: 1; margin: 0; }');
  slides.push('  section.diagram img { max-height: 480px; max-width: 100%; object-fit: contain; }');
  slides.push('  h2 { font-size: 28px; color: #1a1a2e; border-bottom: 2px solid #2563eb; padding-bottom: 8px; }');
  slides.push('  strong { color: #2563eb; }');
  slides.push('  table { font-size: 15px; }');
  slides.push('  th { background: #eff6ff; }');
  slides.push('  li { margin: 6px 0; font-size: 20px; }');
  slides.push('---');
  slides.push('');

  // Title slide
  slides.push('<!-- _class: title -->');
  slides.push('');
  slides.push(`# ${config.title}`);
  slides.push(`## ${config.subtitle}`);
  slides.push('');
  slides.push(`${config.date} | Production v1.0`);
  slides.push('');

  for (const section of sections) {
    // Section divider slide
    slides.push('---');
    slides.push('');
    slides.push('<!-- _class: section-title -->');
    slides.push('');
    slides.push(`# ${section.heading}`);
    slides.push('');

    // Content slide with bullets (if any)
    if (section.bullets.length > 0) {
      slides.push('---');
      slides.push('');
      slides.push(`## ${section.heading}`);
      slides.push('');

      // Take up to 8 bullets per slide
      const bulletChunks = chunkArray(section.bullets, 8);
      for (let i = 0; i < bulletChunks.length; i++) {
        if (i > 0) {
          slides.push('---');
          slides.push('');
          slides.push(`## ${section.heading} (cont.)`);
          slides.push('');
        }
        for (const bullet of bulletChunks[i]) {
          slides.push(bullet);
        }
        slides.push('');
      }
    }

    // Key content summary (first few sentences)
    if (section.bullets.length === 0 && section.content.length > 0) {
      slides.push('---');
      slides.push('');
      slides.push(`## ${section.heading}`);
      slides.push('');

      // Extract meaningful sentences (skip very short ones)
      const meaningful = section.content
        .filter(l => l.length > 30 && !l.startsWith('|'))
        .slice(0, 5);

      for (const line of meaningful) {
        slides.push(`- ${line}`);
      }
      slides.push('');
    }

    // Table slide (if any — first table only)
    if (section.tables.length > 0) {
      slides.push('---');
      slides.push('');
      slides.push(`## ${section.heading}`);
      slides.push('');
      slides.push(section.tables[0]);
      slides.push('');
    }

    // Diagram slide (if any)
    for (const diagramSlug of section.diagrams) {
      const imgPath = `${relDiagramsDir}/${diagramSlug}.png`;
      slides.push('---');
      slides.push('');
      slides.push('<!-- _class: diagram -->');
      slides.push('');
      slides.push(`## ${section.heading}`);
      slides.push('');
      slides.push(`![${section.heading}](${imgPath})`);
      slides.push('');
    }
  }

  return slides.join('\n');
}

function chunkArray(arr, size) {
  const chunks = [];
  for (let i = 0; i < arr.length; i += size) {
    chunks.push(arr.slice(i, i + size));
  }
  return chunks;
}

// ── Main ──

async function main() {
  console.log('╔══════════════════════════════════════════╗');
  console.log('║  Generating Product Summary Slides       ║');
  console.log('╚══════════════════════════════════════════╝\n');

  await mkdir(SLIDES_DIR, { recursive: true });

  for (const source of SOURCES) {
    const srcPath = join(ROOT, source.file);
    if (!existsSync(srcPath)) {
      console.warn(`⚠ File not found: ${source.file}`);
      continue;
    }

    const content = await readFile(srcPath, 'utf-8');
    const sections = parseSections(content);

    // Count total slides (title + per-section)
    let slideCount = 1; // title
    for (const s of sections) {
      slideCount += 1; // section divider
      if (s.bullets.length > 0) slideCount += Math.ceil(s.bullets.length / 8);
      else if (s.content.length > 0) slideCount += 1;
      if (s.tables.length > 0) slideCount += 1;
      slideCount += s.diagrams.length;
    }

    console.log(`📊 ${source.file} → ~${slideCount} slides (${source.lang})`);

    const marpMd = buildProductSlides(sections, source.lang, source);
    const outPath = join(SLIDES_DIR, source.output);
    await writeFile(outPath, marpMd, 'utf-8');

    console.log(`  ✓ ${source.output}`);
  }

  console.log('\n═══ Product summary slides generated ═══');
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
