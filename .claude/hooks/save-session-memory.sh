#!/usr/bin/env bash
# Stop hook: 세션 종료 시 변경 사항 요약을 자동 기록
# dev.to/@suede 패턴 — 세션 간 연속성을 위한 자동 메모리 저장
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}"
[[ ! -d ".git" ]] && exit 0

SUMMARY_FILE="logs/session-summary.jsonl"
mkdir -p logs

# 변경 파일 수집 (unstaged + staged)
CHANGED=$(git diff --name-only HEAD 2>/dev/null | head -30 || true)
STAGED=$(git diff --cached --name-only 2>/dev/null | head -30 || true)
ALL_CHANGES=$(printf '%s\n%s' "$CHANGED" "$STAGED" | sort -u | grep -v '^$' || true)

# KST 타임스탬프 (프로젝트 규칙: 모든 시간 표시는 KST)
# Windows Git Bash에서 TZ 환경변수 미동작 → PowerShell 폴백
TS=$(powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-ddTHH:mm:ss+09:00'" 2>/dev/null \
  || TZ=Asia/Seoul date +"%Y-%m-%dT%H:%M:%S+09:00" 2>/dev/null \
  || date +"%Y-%m-%dT%H:%M:%S")

# 변경 파일 수 (빈 문자열 시 0)
if [[ -z "$ALL_CHANGES" ]]; then
  CHANGED_COUNT=0
else
  CHANGED_COUNT=$(echo "$ALL_CHANGES" | wc -l | tr -d ' ')
fi
if [[ -z "$STAGED" ]]; then
  STAGED_COUNT=0
else
  STAGED_COUNT=$(echo "$STAGED" | wc -l | tr -d ' ')
fi

# 모듈별 변경 감지
MODULES=""
for mod in fdd kiis im deal-mgmt amic-platform; do
  if echo "$ALL_CHANGES" | grep -q "^$mod/"; then
    MODULES="${MODULES}${mod},"
  fi
done
MODULES="${MODULES%,}"

# 커밋되지 않은 변경 여부
if [[ "$CHANGED_COUNT" -gt 0 ]]; then
  UNCOMMITTED="true"
else
  UNCOMMITTED="false"
fi

# 최근 커밋 메시지 (이번 세션에서 커밋했을 수 있음)
LAST_COMMIT=$(git log -1 --format='%s' 2>/dev/null || echo "")
LAST_COMMIT=$(echo "$LAST_COMMIT" | head -c 200)

# 변경 파일 목록 (최대 10개)
FILE_LIST=$(echo "$ALL_CHANGES" | head -10 | tr '\n' ',' | sed 's/,$//')

# jq로 안전한 JSON 생성 (특수 문자 자동 이스케이프)
# --arg는 문자열로 전달, jq 내부에서 tonumber/test로 타입 변환
if command -v jq &>/dev/null; then
  jq -n --compact-output \
    --arg ts "$TS" \
    --arg changed "$CHANGED_COUNT" \
    --arg staged "$STAGED_COUNT" \
    --arg uncommitted "$UNCOMMITTED" \
    --arg modules "$MODULES" \
    --arg last_commit "$LAST_COMMIT" \
    --arg files "$FILE_LIST" \
    '{ts:$ts,changed:($changed|tonumber),staged:($staged|tonumber),uncommitted:($uncommitted|test("true")),modules:$modules,last_commit:$last_commit,files:$files}' \
    >> "$SUMMARY_FILE"
else
  # jq 미설치 폴백: 특수 문자 제거 후 printf
  SAFE_COMMIT=$(echo "$LAST_COMMIT" | tr -d '"\\\n')
  printf '{"ts":"%s","changed":%s,"staged":%s,"uncommitted":%s,"modules":"%s","last_commit":"%s","files":"%s"}\n' \
    "$TS" "$CHANGED_COUNT" "$STAGED_COUNT" "$UNCOMMITTED" "$MODULES" "$SAFE_COMMIT" "$FILE_LIST" \
    >> "$SUMMARY_FILE"
fi

exit 0
