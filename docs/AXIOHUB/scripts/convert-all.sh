#!/usr/bin/env bash
set -euo pipefail

#
# convert-all.sh — Master orchestrator for AxioHub doc conversion
#
# Runs the full pipeline:
#   1. Extract & render Mermaid diagrams to PNG
#   2. Replace code blocks with image refs in markdown copies
#   3. Generate PDFs from markdown (custom Puppeteer script)
#   4. Generate Marp slide decks → PPTX
#
# Usage: npm run build   (or: bash scripts/convert-all.sh)
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD="$ROOT/build"

# Tool paths
NODE="node"
MARP="$ROOT/node_modules/.bin/marp"

echo "╔══════════════════════════════════════════╗"
echo "║  AxioHub Documentation Build Pipeline    ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Root: $ROOT"
echo "Build: $BUILD"
echo ""

# ── Step 0: Clean & create directories ──
echo "▸ Step 0: Preparing build directories..."
rm -rf "$BUILD"
mkdir -p "$BUILD/diagrams/en" "$BUILD/diagrams/tr" "$BUILD/md-with-images" "$BUILD/pdf" "$BUILD/pptx" "$BUILD/slides"
echo "  ✓ Build directories created"
echo ""

# ── Step 1: Extract & render Mermaid diagrams ──
echo "▸ Step 1: Extracting and rendering Mermaid diagrams..."
$NODE "$SCRIPT_DIR/extract-mermaid.mjs"
echo ""

# ── Step 2: Replace Mermaid blocks with image refs ──
echo "▸ Step 2: Replacing Mermaid blocks with image references..."
$NODE "$SCRIPT_DIR/replace-mermaid-with-images.mjs"
echo ""

# ── Step 3: Generate PDFs (custom Puppeteer script) ──
echo "▸ Step 3: Generating PDFs..."
$NODE "$SCRIPT_DIR/generate-pdf.mjs"
echo ""

# ── Step 4: Generate slide deck markdown ──
echo "▸ Step 4: Generating slide decks..."
$NODE "$SCRIPT_DIR/generate-marp-slides.mjs"
$NODE "$SCRIPT_DIR/generate-product-slides.mjs"
echo ""

# ── Step 5: Convert slide markdown to PPTX ──
echo "▸ Step 5: Converting slides to PPTX..."

generate_pptx() {
  local input="$1"
  local output="$2"
  local name
  name="$(basename "$output")"

  if [ ! -f "$input" ]; then
    echo "  ⚠ Slide markdown not found: $input"
    return 1
  fi

  echo "  ⏳ $name..."
  "$MARP" "$input" \
    --pptx \
    --allow-local-files \
    --no-stdin \
    -o "$BUILD/pptx/$name"

  if [ -f "$BUILD/pptx/$name" ]; then
    echo "  ✓ $name"
  else
    echo "  ✗ Failed: $name"
    return 1
  fi
}

generate_pptx "$BUILD/slides/AXIOHUB-ARCHITECTURE-SLIDES.md" "AXIOHUB-ARCHITECTURE-SLIDES.pptx"
generate_pptx "$BUILD/slides/AXIOHUB-MIMARI-SLAYTLAR.md" "AXIOHUB-MIMARI-SLAYTLAR.pptx"
generate_pptx "$BUILD/slides/AXIOHUB-PRODUCT-SUMMARY.md" "AXIOHUB-PRODUCT-SUMMARY.pptx"
generate_pptx "$BUILD/slides/AXIOHUB-URUN-OZETI.md" "AXIOHUB-URUN-OZETI.pptx"
echo ""

# ── Summary ──
echo "╔══════════════════════════════════════════╗"
echo "║  Build Complete!                         ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "📁 Output files:"
echo ""

echo "PDFs:"
ls -la "$BUILD/pdf/"*.pdf 2>/dev/null | awk '{printf "  %-50s %s\n", $NF, $5}' || echo "  (none)"
echo ""

echo "PPTX:"
ls -la "$BUILD/pptx/"*.pptx 2>/dev/null | awk '{printf "  %-50s %s\n", $NF, $5}' || echo "  (none)"
echo ""

echo "Diagrams:"
echo "  EN: $(ls "$BUILD/diagrams/en/"*.png 2>/dev/null | wc -l | tr -d ' ') PNGs"
echo "  TR: $(ls "$BUILD/diagrams/tr/"*.png 2>/dev/null | wc -l | tr -d ' ') PNGs"
