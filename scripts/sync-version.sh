#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# sync-version.sh — VERSION 파일 → 모든 모듈 버전 동기화
# 사용법: bash scripts/sync-version.sh [버전]
#   인자 없으면 VERSION 파일에서 읽음
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION_FILE="$ROOT_DIR/VERSION"

if [ -n "${1:-}" ]; then
  VERSION="$1"
  echo "$VERSION" > "$VERSION_FILE"
else
  if [ ! -f "$VERSION_FILE" ]; then
    echo "❌ VERSION 파일이 없습니다: $VERSION_FILE"
    exit 1
  fi
  VERSION=$(tr -d '[:space:]' < "$VERSION_FILE")
fi

# SemVer 형식 검증
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
  echo "❌ 잘못된 버전 형식: $VERSION (SemVer 필요: X.Y.Z)"
  exit 1
fi

echo "📦 버전 동기화: $VERSION"

# ── 1. amic-platform/package.json ──
PKG="$ROOT_DIR/amic-platform/package.json"
if [ -f "$PKG" ]; then
  # sed로 "version": "..." 교체 (OS 독립적)
  python3 -c "
import json, sys
with open('$PKG', 'r', encoding='utf-8') as f:
    data = json.load(f)
data['version'] = '$VERSION'
with open('$PKG', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write('\n')
" 2>/dev/null || sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$PKG"
  echo "  ✅ amic-platform/package.json → $VERSION"
fi

# ── 2. Python pyproject.toml 파일들 ──
for TOML in \
  "$ROOT_DIR/deal-mgmt/pyproject.toml" \
  "$ROOT_DIR/kiis/pyproject.toml" \
  "$ROOT_DIR/fdd/backend/pyproject.toml"; do
  if [ -f "$TOML" ]; then
    python3 -c "
import re, pathlib
p = pathlib.Path('$TOML')
text = p.read_text(encoding='utf-8')
text = re.sub(r'^version\s*=\s*\"[^\"]*\"', 'version = \"$VERSION\"', text, count=1, flags=re.MULTILINE)
p.write_text(text, encoding='utf-8')
" 2>/dev/null || sed -i "s/^version = \"[^\"]*\"/version = \"$VERSION\"/" "$TOML"
    REL=$(echo "$TOML" | sed "s|$ROOT_DIR/||")
    echo "  ✅ $REL → $VERSION"
  fi
done

echo ""
echo "✅ 모든 모듈 버전이 $VERSION으로 동기화되었습니다."
