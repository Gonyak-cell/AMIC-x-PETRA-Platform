#!/usr/bin/env bash
# Auto FDD — Frontend Bundle Size Analysis
# Usage: ./scripts/fe_bundle_analysis.sh [--json] [--ci]
#
# SLA: Initial bundle < 500KB (gzipped)

set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"
OUTPUT_JSON="${1:-false}"
CI_MODE="${2:-false}"
SLA_INITIAL_KB=500
SLA_TOTAL_KB=2000

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[BUNDLE]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[FAIL]${NC} $*"; }
info() { echo -e "${CYAN}[INFO]${NC} $*"; }

# Parse args
for arg in "$@"; do
    case $arg in
        --json) OUTPUT_JSON="true" ;;
        --ci)   CI_MODE="true" ;;
    esac
done

# ── Build ──
log "Building frontend for production..."
cd "$FRONTEND_DIR"

if [ ! -f "package.json" ]; then
    err "No package.json found in $FRONTEND_DIR"
    exit 1
fi

# Install deps if needed
if [ ! -d "node_modules" ]; then
    npm ci --silent
fi

# Build
npm run build -- --mode production 2>/dev/null || npm run build 2>/dev/null

DIST_DIR="$FRONTEND_DIR/dist"
if [ ! -d "$DIST_DIR" ]; then
    err "Build output not found at $DIST_DIR"
    exit 1
fi

# ── Analyze ──
log "Analyzing bundle sizes..."
echo ""

# Total sizes
TOTAL_JS=0
TOTAL_CSS=0
TOTAL_ASSETS=0
TOTAL_HTML=0

declare -A FILE_SIZES

# JS files
echo "JavaScript files:"
echo "  ────────────────────────────────────────"
while IFS= read -r -d '' file; do
    size=$(stat -f%z "$file" 2>/dev/null || stat --printf="%s" "$file" 2>/dev/null || echo 0)
    size_kb=$((size / 1024))
    gzip_size=$(gzip -c "$file" 2>/dev/null | wc -c | tr -d ' ')
    gzip_kb=$((gzip_size / 1024))
    name=$(basename "$file")
    TOTAL_JS=$((TOTAL_JS + gzip_size))

    # Color based on size
    if [ "$gzip_kb" -gt 200 ]; then
        color="$RED"
    elif [ "$gzip_kb" -gt 100 ]; then
        color="$YELLOW"
    else
        color="$GREEN"
    fi
    printf "  ${color}%-40s %6d KB → %6d KB (gzip)${NC}\n" "$name" "$size_kb" "$gzip_kb"
done < <(find "$DIST_DIR" -name "*.js" -print0 2>/dev/null | sort -z)

# CSS files
echo ""
echo "CSS files:"
echo "  ────────────────────────────────────────"
while IFS= read -r -d '' file; do
    size=$(stat -f%z "$file" 2>/dev/null || stat --printf="%s" "$file" 2>/dev/null || echo 0)
    size_kb=$((size / 1024))
    gzip_size=$(gzip -c "$file" 2>/dev/null | wc -c | tr -d ' ')
    gzip_kb=$((gzip_size / 1024))
    name=$(basename "$file")
    TOTAL_CSS=$((TOTAL_CSS + gzip_size))
    printf "  %-40s %6d KB → %6d KB (gzip)\n" "$name" "$size_kb" "$gzip_kb"
done < <(find "$DIST_DIR" -name "*.css" -print0 2>/dev/null | sort -z)

# Asset files
echo ""
TOTAL_ASSETS_RAW=0
while IFS= read -r -d '' file; do
    size=$(stat -f%z "$file" 2>/dev/null || stat --printf="%s" "$file" 2>/dev/null || echo 0)
    TOTAL_ASSETS_RAW=$((TOTAL_ASSETS_RAW + size))
done < <(find "$DIST_DIR" \( -name "*.png" -o -name "*.jpg" -o -name "*.svg" -o -name "*.woff2" -o -name "*.woff" -o -name "*.ico" \) -print0 2>/dev/null)
TOTAL_ASSETS=$TOTAL_ASSETS_RAW

# ── Summary ──
TOTAL_JS_KB=$((TOTAL_JS / 1024))
TOTAL_CSS_KB=$((TOTAL_CSS / 1024))
TOTAL_ASSETS_KB=$((TOTAL_ASSETS / 1024))
TOTAL_KB=$((TOTAL_JS_KB + TOTAL_CSS_KB + TOTAL_ASSETS_KB))

# Initial load = main JS + main CSS (index chunks)
INITIAL_JS=0
while IFS= read -r -d '' file; do
    name=$(basename "$file")
    if [[ "$name" == index-* ]] || [[ "$name" == main-* ]] || [[ "$name" == index.* ]]; then
        gzip_size=$(gzip -c "$file" 2>/dev/null | wc -c | tr -d ' ')
        INITIAL_JS=$((INITIAL_JS + gzip_size))
    fi
done < <(find "$DIST_DIR" -name "*.js" -print0 2>/dev/null)
INITIAL_CSS=0
while IFS= read -r -d '' file; do
    name=$(basename "$file")
    if [[ "$name" == index-* ]] || [[ "$name" == main-* ]] || [[ "$name" == index.* ]]; then
        gzip_size=$(gzip -c "$file" 2>/dev/null | wc -c | tr -d ' ')
        INITIAL_CSS=$((INITIAL_CSS + gzip_size))
    fi
done < <(find "$DIST_DIR" -name "*.css" -print0 2>/dev/null)
INITIAL_KB=$(( (INITIAL_JS + INITIAL_CSS) / 1024 ))

echo ""
echo "════════════════════════════════════════════"
echo "  BUNDLE SIZE SUMMARY"
echo "════════════════════════════════════════════"
echo ""
echo "  Total JS (gzip):     ${TOTAL_JS_KB} KB"
echo "  Total CSS (gzip):    ${TOTAL_CSS_KB} KB"
echo "  Total Assets:        ${TOTAL_ASSETS_KB} KB"
echo "  ──────────────────────────────"
echo "  Total Bundle:        ${TOTAL_KB} KB"
echo "  Initial Load:        ${INITIAL_KB} KB"
echo ""

# SLA Check
PASSED=true

if [ "$INITIAL_KB" -le "$SLA_INITIAL_KB" ]; then
    log "Initial Load: ${INITIAL_KB} KB <= ${SLA_INITIAL_KB} KB SLA — PASS"
else
    err "Initial Load: ${INITIAL_KB} KB > ${SLA_INITIAL_KB} KB SLA — FAIL"
    PASSED=false
fi

if [ "$TOTAL_KB" -le "$SLA_TOTAL_KB" ]; then
    log "Total Bundle: ${TOTAL_KB} KB <= ${SLA_TOTAL_KB} KB SLA — PASS"
else
    err "Total Bundle: ${TOTAL_KB} KB > ${SLA_TOTAL_KB} KB SLA — FAIL"
    PASSED=false
fi

echo ""

# ── JSON Output ──
if [ "$OUTPUT_JSON" = "true" ]; then
    cat <<ENDJSON
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "total_js_kb": ${TOTAL_JS_KB},
  "total_css_kb": ${TOTAL_CSS_KB},
  "total_assets_kb": ${TOTAL_ASSETS_KB},
  "total_bundle_kb": ${TOTAL_KB},
  "initial_load_kb": ${INITIAL_KB},
  "sla_initial_kb": ${SLA_INITIAL_KB},
  "sla_total_kb": ${SLA_TOTAL_KB},
  "initial_passed": $([ "$INITIAL_KB" -le "$SLA_INITIAL_KB" ] && echo "true" || echo "false"),
  "total_passed": $([ "$TOTAL_KB" -le "$SLA_TOTAL_KB" ] && echo "true" || echo "false")
}
ENDJSON
fi

# ── CI Exit Code ──
if [ "$CI_MODE" = "true" ] && [ "$PASSED" = "false" ]; then
    exit 1
fi
