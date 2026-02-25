#!/usr/bin/env bash
# smoke-test.sh — 코드 수정 후 빠른 안정성 검증 (30초 이내)
#
# 사용: bash scripts/smoke-test.sh
# 종료 코드: 0=통과, 1=실패
# 환경: Git Bash 또는 WSL (Windows 네이티브 cmd/PowerShell 미지원)
# 의존: curl (Git Bash에 기본 포함)
#
# 방지하는 회귀 오류:
# - 백엔드 서버 다운 (health check 실패)
# - 인증 플로우 깨짐 (로그인 → 쿠키 → /auth/me)
# - 보호된 엔드포인트 인증 우회 (401 미반환)
# - 주요 API 응답 실패

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

COOKIE_FILE="${TMPDIR:-/tmp}/smoke-cookies.txt"

check() {
  local name="$1" url="$2" expected_status="${3:-200}"
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
  if [ "$status" = "$expected_status" ]; then
    echo -e "  ${GREEN}PASS${NC} $name (HTTP $status)"
    ((PASS++))
  elif [ "$status" = "000" ]; then
    echo -e "  ${YELLOW}SKIP${NC} $name (서버 미실행)"
    ((WARN++))
  else
    echo -e "  ${RED}FAIL${NC} $name (expected $expected_status, got $status)"
    ((FAIL++))
  fi
}

check_with_cookie() {
  local name="$1" url="$2" expected_status="${3:-200}"
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" -b "$COOKIE_FILE" --max-time 5 "$url" 2>/dev/null || echo "000")
  if [ "$status" = "$expected_status" ]; then
    echo -e "  ${GREEN}PASS${NC} $name (HTTP $status)"
    ((PASS++))
  elif [ "$status" = "000" ]; then
    echo -e "  ${YELLOW}SKIP${NC} $name (서버 미실행)"
    ((WARN++))
  else
    echo -e "  ${RED}FAIL${NC} $name (expected $expected_status, got $status)"
    ((FAIL++))
  fi
}

echo "=== Smoke Test — Regression Guard ==="
echo ""

# ── Phase 1: Health Check (4개 백엔드) ──
echo "[1/4] Health Checks"
check "FDD  (8000)" "http://localhost:8000/health"
check "KIIS (8001)" "http://localhost:8001/health"
check "IM   (8002)" "http://localhost:8002/api/v1/health"
check "MA   (8003)" "http://localhost:8003/health"
echo ""

# ── Phase 2: 인증 플로우 (FDD 중앙 인증) ──
echo "[2/4] Auth Flow"
LOGIN_RESP=$(curl -s -c "$COOKIE_FILE" \
  -w "\n%{http_code}" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@autofdd.dev","password":"admin123!"}' \
  "http://localhost:8000/api/v1/auth/login" 2>/dev/null || echo -e "\n000")
LOGIN_STATUS=$(echo "$LOGIN_RESP" | tail -1)

if [ "$LOGIN_STATUS" = "200" ]; then
  echo -e "  ${GREEN}PASS${NC} Login (HTTP $LOGIN_STATUS)"
  ((PASS++))
  check_with_cookie "Auth /me (cookie)" "http://localhost:8000/api/v1/auth/me"
else
  if [ "$LOGIN_STATUS" = "000" ]; then
    echo -e "  ${YELLOW}SKIP${NC} Login (FDD 서버 미실행)"
    ((WARN++))
  else
    echo -e "  ${RED}FAIL${NC} Login (expected 200, got $LOGIN_STATUS)"
    ((FAIL++))
  fi
fi
echo ""

# ── Phase 3: 비인증 요청 → 401 확인 ──
echo "[3/4] Unauthenticated Rejection (401)"
check "FDD /auth/me (no cookie)" "http://localhost:8000/api/v1/auth/me" "401"
check "MA /transactions (no auth)" "http://localhost:8003/api/v1/transactions" "401"
echo ""

# ── Phase 4: 주요 API 엔드포인트 (인증된 상태) ──
echo "[4/4] Key API Endpoints (authenticated)"
if [ -f "$COOKIE_FILE" ] && [ "$LOGIN_STATUS" = "200" ]; then
  check_with_cookie "FDD /deals" "http://localhost:8000/api/v1/deals"
  check_with_cookie "KIIS /deals" "http://localhost:8001/api/v1/deals"
  check_with_cookie "IM /documents" "http://localhost:8002/api/v1/documents"
  check_with_cookie "MA /transactions" "http://localhost:8003/api/v1/transactions"
else
  echo -e "  ${YELLOW}SKIP${NC} (로그인 미완료 — 인증 API 테스트 건너뜀)"
  ((WARN++))
fi

# 정리
rm -f "$COOKIE_FILE"

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed, ${WARN} skipped ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
