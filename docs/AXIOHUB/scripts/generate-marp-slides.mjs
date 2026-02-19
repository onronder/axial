#!/usr/bin/env node
/**
 * generate-marp-slides.mjs
 *
 * Generates Marp-format markdown for architecture diagram slide decks.
 * One diagram per slide, with title slide.
 * Produces EN and TR versions.
 *
 * Usage: node scripts/generate-marp-slides.mjs
 */

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const BUILD = join(ROOT, 'build');
const SLIDES_DIR = join(BUILD, 'slides');
const THEME_PATH = join(__dirname, 'marp-theme.css');

const SOURCES = [
  {
    file: 'AXIOHUB-ARCHITECTURE-DIAGRAMS.md',
    lang: 'en',
    output: 'AXIOHUB-ARCHITECTURE-SLIDES.md',
    title: 'AxioHub Architecture',
    subtitle: 'System Diagrams & Data Flows',
    date: 'February 2026',
  },
  {
    file: 'AXIOHUB-MIMARI-DIYAGRAMLAR.md',
    lang: 'tr',
    output: 'AXIOHUB-MIMARI-SLAYTLAR.md',
    title: 'AxioHub Mimari',
    subtitle: 'Sistem Diyagramları ve Veri Akışları',
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
 * Extract diagram sections: heading + slug for each mermaid block.
 */
function extractDiagramSections(content) {
  const sections = [];
  const lines = content.split('\n');
  let currentHeading = '';
  let blockIndex = 0;

  for (const line of lines) {
    const headingMatch = line.match(/^##\s+(.+)/);
    if (headingMatch) {
      currentHeading = headingMatch[1].trim();
    }

    if (line.trim() === '```mermaid') {
      blockIndex++;
      const slug = slugify(currentHeading) || `diagram-${blockIndex}`;
      sections.push({ heading: currentHeading, slug });
    }
  }

  return sections;
}

/**
 * Build Marp markdown with one diagram per slide.
 */
function buildMarpSlides(sections, lang, config) {
  const diagramsDir = join(BUILD, 'diagrams', lang);
  // Relative path from slides/ to diagrams/{lang}/
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
  slides.push('  section.title h1 { font-size: 48px; border: none; color: white; }');
  slides.push('  section.title h2 { font-size: 24px; font-weight: 400; color: #94a3b8; border: none; }');
  slides.push('  section.title p { color: #94a3b8; font-size: 16px; }');
  slides.push('  section.diagram { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding: 40px 50px 30px; }');
  slides.push('  section.diagram h2 { font-size: 26px; color: #1a1a2e; border-bottom: 2px solid #2563eb; width: 100%; padding-bottom: 8px; margin: 0 0 12px 0; flex-shrink: 0; }');
  slides.push('  section.diagram p { display: flex; justify-content: center; align-items: center; flex: 1; margin: 0; }');
  slides.push('  section.diagram img { max-height: 480px; max-width: 100%; object-fit: contain; }');
  slides.push('  h2 { font-size: 28px; color: #1a1a2e; border-bottom: 2px solid #2563eb; padding-bottom: 8px; }');
  slides.push('  strong { color: #2563eb; }');
  slides.push('---');
  slides.push('');

  // Title slide
  slides.push('<!-- _class: title -->');
  slides.push('');
  slides.push(`# ${config.title}`);
  slides.push(`## ${config.subtitle}`);
  slides.push('');
  slides.push(`${config.date} | v1.0`);
  slides.push('');

  // One diagram per slide
  for (const section of sections) {
    const imgPath = `${relDiagramsDir}/${section.slug}.png`;
    const pngExists = existsSync(join(diagramsDir, `${section.slug}.png`));

    slides.push('---');
    slides.push('');
    slides.push('<!-- _class: diagram -->');
    slides.push('');
    slides.push(`## ${section.heading}`);
    slides.push('');
    if (pngExists) {
      slides.push(`![${section.heading}](${imgPath})`);
    } else {
      slides.push(`> Diagram: ${section.slug} (render pending)`);
    }
    slides.push('');
  }

  return slides.join('\n');
}

// ── Main ──

async function main() {
  console.log('╔══════════════════════════════════════════╗');
  console.log('║  Generating Architecture Slide Decks     ║');
  console.log('╚══════════════════════════════════════════╝\n');

  await mkdir(SLIDES_DIR, { recursive: true });

  for (const source of SOURCES) {
    const srcPath = join(ROOT, source.file);
    if (!existsSync(srcPath)) {
      console.warn(`⚠ File not found: ${source.file}`);
      continue;
    }

    const content = await readFile(srcPath, 'utf-8');
    const sections = extractDiagramSections(content);

    console.log(`📊 ${source.file} → ${sections.length} slides (${source.lang})`);

    const marpMd = buildMarpSlides(sections, source.lang, source);
    const outPath = join(SLIDES_DIR, source.output);
    await writeFile(outPath, marpMd, 'utf-8');

    console.log(`  ✓ ${source.output}`);
  }

  console.log('\n═══ Architecture slides generated ═══');
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
