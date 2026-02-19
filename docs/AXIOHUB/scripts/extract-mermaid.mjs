#!/usr/bin/env node
/**
 * extract-mermaid.mjs
 *
 * Parses AxioHub markdown files, extracts Mermaid code blocks,
 * writes them to .mmd files, and renders each to high-res PNG via mmdc.
 *
 * Usage: node scripts/extract-mermaid.mjs
 */

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const BUILD = join(ROOT, 'build');
const MMDC = join(ROOT, 'node_modules', '.bin', 'mmdc');
const CONFIG = join(__dirname, 'mermaid-config.json');

// Source files mapped to language keys
const SOURCE_FILES = [
  { file: 'AXIOHUB-ARCHITECTURE-DIAGRAMS.md', lang: 'en' },
  { file: 'AXIOHUB-PRODUCT-DOCUMENTATION.md', lang: 'en' },
  { file: 'AXIOHUB-MIMARI-DIYAGRAMLAR.md', lang: 'tr' },
  { file: 'AXIOHUB-URUN-DOKUMANTASYONU.md', lang: 'tr' },
];

/**
 * Slugify a heading string for filenames.
 * "5. File Upload & Ingestion Pipeline" → "05-file-upload-ingestion-pipeline"
 */
function slugify(heading) {
  // Extract leading number if present
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
 * Detect diagram orientation from first line.
 * Returns { width, height } for mmdc rendering.
 */
function detectOrientation(mermaidCode) {
  const firstLine = mermaidCode.trim().split('\n')[0].trim();
  // LR (left-to-right) diagrams are landscape
  if (/^(graph|flowchart)\s+LR/i.test(firstLine)) {
    return { width: 2000, height: 1000 };
  }
  // Sequence diagrams tend to be taller
  if (/^sequenceDiagram/i.test(firstLine)) {
    return { width: 1600, height: 1400 };
  }
  // TB (top-to-bottom) is the default portrait
  return { width: 1600, height: 1200 };
}

/**
 * Extract all mermaid blocks from a markdown file.
 * Returns array of { heading, slug, code }.
 */
function extractMermaidBlocks(content) {
  const blocks = [];
  const lines = content.split('\n');
  let currentHeading = 'untitled';
  let inMermaid = false;
  let mermaidCode = '';
  let blockIndex = 0;

  for (const line of lines) {
    // Track the most recent heading
    const headingMatch = line.match(/^##\s+(.+)/);
    if (headingMatch) {
      currentHeading = headingMatch[1].trim();
    }

    // Detect mermaid block start
    if (line.trim() === '```mermaid') {
      inMermaid = true;
      mermaidCode = '';
      continue;
    }

    // Detect block end
    if (inMermaid && line.trim() === '```') {
      inMermaid = false;
      blockIndex++;
      const slug = slugify(currentHeading) || `diagram-${blockIndex}`;
      blocks.push({
        heading: currentHeading,
        slug,
        code: mermaidCode.trim(),
      });
      continue;
    }

    // Accumulate mermaid code
    if (inMermaid) {
      mermaidCode += line + '\n';
    }
  }

  return blocks;
}

/**
 * Render a single .mmd file to PNG using mmdc.
 */
async function renderDiagram(mmdPath, pngPath, dimensions) {
  const args = [
    '-i', mmdPath,
    '-o', pngPath,
    '-c', CONFIG,
    '-s', '2',           // 2x scale for high-res
    '-w', String(dimensions.width),
    '-H', String(dimensions.height),
    '-b', 'white',
  ];

  try {
    await execFileAsync(MMDC, args, { timeout: 30000 });
    return true;
  } catch (err) {
    console.error(`  ✗ Failed to render ${mmdPath}: ${err.message}`);
    return false;
  }
}

// ── Main ──

async function main() {
  console.log('╔══════════════════════════════════════════╗');
  console.log('║  Extracting & Rendering Mermaid Diagrams ║');
  console.log('╚══════════════════════════════════════════╝\n');

  let totalBlocks = 0;
  let totalRendered = 0;

  for (const { file, lang } of SOURCE_FILES) {
    const filePath = join(ROOT, file);
    if (!existsSync(filePath)) {
      console.warn(`⚠ File not found: ${file}`);
      continue;
    }

    const content = await readFile(filePath, 'utf-8');
    const blocks = extractMermaidBlocks(content);

    if (blocks.length === 0) {
      console.log(`  ${file}: no mermaid blocks found`);
      continue;
    }

    console.log(`📄 ${file} → ${blocks.length} diagrams (${lang})`);

    const diagramDir = join(BUILD, 'diagrams', lang);
    await mkdir(diagramDir, { recursive: true });

    for (const block of blocks) {
      totalBlocks++;
      const mmdPath = join(diagramDir, `${block.slug}.mmd`);
      const pngPath = join(diagramDir, `${block.slug}.png`);
      const dimensions = detectOrientation(block.code);

      // Write .mmd source
      await writeFile(mmdPath, block.code, 'utf-8');

      // Render to PNG
      const ok = await renderDiagram(mmdPath, pngPath, dimensions);
      if (ok) {
        totalRendered++;
        console.log(`  ✓ ${block.slug}.png (${dimensions.width}×${dimensions.height})`);
      }
    }

    console.log('');
  }

  console.log(`\n═══ Summary: ${totalRendered}/${totalBlocks} diagrams rendered ═══`);
  if (totalRendered < totalBlocks) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
