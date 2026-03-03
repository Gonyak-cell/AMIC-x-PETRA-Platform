#!/bin/bash
# PreToolUse hook: 인프라 보호 대상 파일 편집 차단 (infra-freeze.md 규칙 자동 강제)
# Tier 1: docker-compose*.yml, deploy.yml — 절대 보호
# Tier 2: nginx/prod*.conf, docker-entrypoint.sh — 강한 보호
if ! command -v jq &>/dev/null; then
  echo "BLOCKED: jq가 설치되어 있지 않아 인프라 파일 보호 검사를 수행할 수 없습니다." >&2
  exit 2
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || FILE_PATH=""

[[ -z "$FILE_PATH" ]] && exit 0

# Tier 1: 절대 보호 (사용자 명시적 승인 필수)
TIER1_PATTERNS=(
  "docker-compose.yml"
  "docker-compose.prod.yml"
  "docker-compose.ssl.yml"
  ".github/workflows/deploy.yml"
)

for p in "${TIER1_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$p"* ]]; then
    echo "BLOCKED: '$FILE_PATH' — 인프라 Tier 1 보호 대상 (infra-freeze). image 태그, workers, 환경변수 게이트 등 배포 안전장치 포함. 사용자 명시적 승인 필요." >&2
    exit 2
  fi
done

# Tier 2: 강한 보호 (사용자 확인 필요)
TIER2_PATTERNS=(
  "nginx/prod.conf"
  "nginx/prod-nossl.conf"
  "docker-entrypoint.sh"
)

for p in "${TIER2_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$p"* ]]; then
    echo "BLOCKED: '$FILE_PATH' — 인프라 Tier 2 보호 대상 (infra-freeze). 프로덕션 라우팅/시작 로직 포함. 사용자 확인 필요." >&2
    exit 2
  fi
done

exit 0
