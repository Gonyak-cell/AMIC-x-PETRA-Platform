#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# sync-version.sh — VERSION 파일 → 모든 모듈 버전 동기화 + 릴리즈 노트 자동 생성
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

# ── 3. 릴리즈 노트 자동 생성 ──
RELEASE_FILE="$ROOT_DIR/amic-platform/src/lib/releaseNotes.ts"

if [ -f "$RELEASE_FILE" ]; then
  # 이미 해당 버전의 릴리즈 노트가 있으면 스킵
  if grep -q "version: \"$VERSION\"" "$RELEASE_FILE"; then
    echo "  ⏭️  릴리즈 노트에 v$VERSION 이미 존재 — 스킵"
  else
    echo "  📝 릴리즈 노트 자동 생성 중..."

    # 직전 버전 태그 또는 chore: bump 커밋을 기준으로 feat/fix 커밋 추출
    PREV_BUMP=$(git log --oneline --all --grep="bump version" --format="%H" -1 2>/dev/null || echo "")
    if [ -z "$PREV_BUMP" ]; then
      PREV_BUMP=$(git rev-list --max-parents=0 HEAD 2>/dev/null || echo "HEAD~50")
    fi

    python3 "$ROOT_DIR/scripts/generate-release-note.py" "$VERSION" "$PREV_BUMP" "$RELEASE_FILE"
  fi
fi

echo ""
echo "✅ 모든 모듈 버전이 $VERSION으로 동기화되었습니다."
