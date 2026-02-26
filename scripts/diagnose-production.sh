#!/usr/bin/env bash
# ============================================================
# AMIC x PETRA Platform — Production Diagnostic Script
# ============================================================
# 프로덕션 환경의 전 모듈을 한번에 점검하는 통합 진단 스크립트.
# 에러 발생 시 이 스크립트를 먼저 실행하여 전체 상태를 파악한 후 수정한다.
#
# 사용법:
#   bash scripts/diagnose-production.sh          # 전체 진단 (대화형)
#   bash scripts/diagnose-production.sh --ci      # CI 모드 (실패 시 exit 1)
# ============================================================

set -uo pipefail

# ── 설정 ──
CI_MODE=false
[[ "${1:-}" == "--ci" ]] && CI_MODE=true

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
if [ -f docker-compose.ssl.yml ]; then
  COMPOSE="$COMPOSE -f docker-compose.ssl.yml"
fi

PASS_COUNT=0
FAIL_COUNT=0
FAILURES=()
FIXES=()

# ── 유틸리티 ──
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

ok()   { echo -e "  ├─ $1 ${GREEN}✓${NC} $2"; }
fail() { echo -e "  ├─ $1 ${RED}✗${NC} $2"; }
warn() { echo -e "  ├─ $1 ${YELLOW}⚠${NC} $2"; }

section_result() {
  local name=$1 passed=$2
  if $passed; then
    echo -e "  ${GREEN}RESULT: PASS${NC}"
    ((PASS_COUNT++))
  else
    echo -e "  ${RED}RESULT: FAIL${NC}"
    ((FAIL_COUNT++))
  fi
  echo ""
}

# ── 헤더 ──
NOW=$(date '+%Y-%m-%d %H:%M:%S %Z')
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   AMIC PRODUCTION DIAGNOSTIC REPORT          ║${NC}"
echo -e "${BOLD}║   $NOW                  ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# [1/10] 컨테이너 상태
# ============================================================
echo -e "${CYAN}[1/10] Container Status${NC}"
SECTION_OK=true

SERVICES=(
  "frontend" "nginx" "fdd-api" "fdd-db" "fdd-pptx"
  "kiis-api" "kiis-db" "kiis-redis" "kiis-es"
  "im-api" "im-db" "im-redis" "im-celery-worker" "im-celery-beat"
  "deal-mgmt-api" "deal-mgmt-db"
)

RUNNING=0
TOTAL=${#SERVICES[@]}

for svc in "${SERVICES[@]}"; do
  STATUS=$($COMPOSE ps --format '{{.State}}' "$svc" 2>/dev/null || echo "missing")
  RESTARTS=$($COMPOSE ps --format '{{.Status}}' "$svc" 2>/dev/null || echo "unknown")
  if [[ "$STATUS" == "running" ]]; then
    ok "$svc" "running ($RESTARTS)"
    ((RUNNING++))
  else
    fail "$svc" "$STATUS"
    SECTION_OK=false
    FAILURES+=("[1] Container: $svc is $STATUS")
    FIXES+=("docker compose up -d $svc")
  fi
done

echo -e "  └─ $RUNNING/$TOTAL running"
section_result "Container Status" $SECTION_OK

# ============================================================
# [2/10] DB 연결 & 비밀번호
# ============================================================
echo -e "${CYAN}[2/10] DB Connection & Password${NC}"
SECTION_OK=true

declare -A DB_MAP=(
  ["fdd-db"]="autofdd:autofdd"
  ["kiis-db"]="kiis_user:kiis"
  ["im-db"]="postgres:imgen"
  ["deal-mgmt-db"]="deal_mgmt_user:deal_mgmt"
)

for svc in fdd-db kiis-db im-db deal-mgmt-db; do
  IFS=':' read -r user db <<< "${DB_MAP[$svc]}"
  RESULT=$($COMPOSE exec -T "$svc" psql -U "$user" -d "$db" -c "SELECT 1" 2>&1)
  if echo "$RESULT" | grep -q "1 row"; then
    ok "$svc ($user@$db)" "SELECT 1 OK"
  else
    fail "$svc ($user@$db)" "연결 실패"
    SECTION_OK=false
    FAILURES+=("[2] DB: $svc 연결 실패 — 비밀번호 불일치 가능")
    FIXES+=("docker exec \$(docker compose ps -q $svc) psql -U $user -d $db -c \"ALTER USER $user WITH PASSWORD '<.env의 비밀번호>';\"")
  fi
done

section_result "DB Connection" $SECTION_OK

# ============================================================
# [3/10] DB 마이그레이션 상태
# ============================================================
echo -e "${CYAN}[3/10] DB Migrations${NC}"
SECTION_OK=true

declare -A MIGRATION_SVC=(
  ["fdd"]="fdd-api"
  ["kiis"]="kiis-api"
  ["im"]="im-api"
  ["deal-mgmt"]="deal-mgmt-api"
)

for mod in fdd kiis im deal-mgmt; do
  svc="${MIGRATION_SVC[$mod]}"
  CURRENT=$($COMPOSE exec -T "$svc" alembic current 2>&1 | grep -oP '[a-f0-9]+' | head -1 || echo "unknown")
  HEAD=$($COMPOSE exec -T "$svc" alembic heads 2>&1 | grep -oP '[a-f0-9]+' | head -1 || echo "unknown")

  if [ "$CURRENT" = "$HEAD" ] && [ "$CURRENT" != "unknown" ]; then
    ok "$mod" "current=$CURRENT head=$HEAD"
  elif [ "$CURRENT" = "unknown" ] && [ "$HEAD" = "unknown" ]; then
    warn "$mod" "alembic 미사용 또는 접근 불가"
  else
    fail "$mod" "current=$CURRENT ≠ head=$HEAD — 미적용 마이그레이션 있음"
    SECTION_OK=false
    FAILURES+=("[3] Migration: $mod 마이그레이션 미적용 (current=$CURRENT, head=$HEAD)")
    FIXES+=("$COMPOSE exec -T $svc alembic upgrade head")
  fi
done

section_result "DB Migrations" $SECTION_OK

# ============================================================
# [4/10] JWT Secret 일관성
# ============================================================
echo -e "${CYAN}[4/10] JWT Secret Consistency${NC}"
SECTION_OK=true

JWT_VALUES=()
API_SERVICES=("fdd-api" "kiis-api" "im-api" "deal-mgmt-api")

for svc in "${API_SERVICES[@]}"; do
  JWT=$($COMPOSE exec -T "$svc" env 2>/dev/null | grep -E "^JWT_SECRET=" | head -1 | cut -d= -f2- || echo "MISSING")
  JWT=${JWT:-MISSING}
  # 마스킹 (앞 8자만 표시)
  if [ ${#JWT} -gt 8 ] && [ "$JWT" != "MISSING" ]; then
    MASKED="${JWT:0:8}..."
  else
    MASKED="$JWT"
  fi

  # 기본값 검출
  if [[ "$JWT" == "change-me-in-production" ]] || [[ "$JWT" == "dev-shared-jwt-secret-change-in-production" ]]; then
    fail "$svc" "JWT_SECRET=$MASKED (기본값 사용!)"
    SECTION_OK=false
    FAILURES+=("[4] JWT: $svc 기본값 JWT_SECRET 사용 중")
    FIXES+=("docker-compose.prod.yml의 $svc에 JWT_SECRET: \${SHARED_JWT_SECRET} 추가")
  elif [ "$JWT" = "MISSING" ]; then
    fail "$svc" "JWT_SECRET=MISSING"
    SECTION_OK=false
    FAILURES+=("[4] JWT: $svc JWT_SECRET 환경변수 누락")
    FIXES+=("docker-compose.prod.yml의 $svc에 JWT_SECRET: \${SHARED_JWT_SECRET} 추가")
  else
    ok "$svc" "JWT_SECRET=$MASKED"
    JWT_VALUES+=("$JWT")
  fi
done

# 값 일관성 확인
if [ ${#JWT_VALUES[@]} -gt 1 ]; then
  FIRST="${JWT_VALUES[0]}"
  for val in "${JWT_VALUES[@]}"; do
    if [ "$val" != "$FIRST" ]; then
      fail "일관성" "모듈간 JWT_SECRET 값이 다름!"
      SECTION_OK=false
      FAILURES+=("[4] JWT: 모듈간 JWT_SECRET 값 불일치 — 크로스 모듈 인증 실패")
      FIXES+=(".env의 SHARED_JWT_SECRET 값을 통일하고 docker compose up -d --force-recreate")
      break
    fi
  done
fi

section_result "JWT Consistency" $SECTION_OK

# ============================================================
# [5/10] CORS 설정
# ============================================================
echo -e "${CYAN}[5/10] CORS Configuration${NC}"
SECTION_OK=true

# FDD: CORS_ORIGINS (str, 쉼표 구분)
FDD_CORS=$($COMPOSE exec -T fdd-api env 2>/dev/null | grep -E "^CORS_ORIGINS=" | cut -d= -f2- || echo "MISSING")
if [ -n "$FDD_CORS" ] && [ "$FDD_CORS" != "MISSING" ]; then
  ok "fdd-api" "CORS_ORIGINS=\"${FDD_CORS:0:50}...\" (str)"
else
  fail "fdd-api" "CORS_ORIGINS 누락"
  SECTION_OK=false
  FAILURES+=("[5] CORS: fdd-api CORS_ORIGINS 환경변수 누락")
fi

# KIIS: ALLOWED_ORIGINS (json 배열)
KIIS_CORS=$($COMPOSE exec -T kiis-api env 2>/dev/null | grep -E "^ALLOWED_ORIGINS=" | cut -d= -f2- || echo "MISSING")
if echo "$KIIS_CORS" | grep -qP '^\['; then
  ok "kiis-api" "ALLOWED_ORIGINS=${KIIS_CORS:0:50}... (json)"
elif [ "$KIIS_CORS" != "MISSING" ]; then
  warn "kiis-api" "ALLOWED_ORIGINS 형식 비정상 (JSON 배열 필요): $KIIS_CORS"
  SECTION_OK=false
  FAILURES+=("[5] CORS: kiis-api ALLOWED_ORIGINS 형식 오류 — JSON 배열 필요")
else
  fail "kiis-api" "ALLOWED_ORIGINS 누락"
  SECTION_OK=false
fi

# IM: CORS_ORIGINS (json 배열)
IM_CORS=$($COMPOSE exec -T im-api env 2>/dev/null | grep -E "^CORS_ORIGINS=" | cut -d= -f2- || echo "MISSING")
if echo "$IM_CORS" | grep -qP '^\['; then
  ok "im-api" "CORS_ORIGINS=${IM_CORS:0:50}... (json)"
elif [ "$IM_CORS" != "MISSING" ]; then
  warn "im-api" "CORS_ORIGINS 형식 비정상 (JSON 배열 필요)"
  SECTION_OK=false
else
  fail "im-api" "CORS_ORIGINS 누락"
  SECTION_OK=false
fi

# MA: ALLOWED_ORIGINS (json 배열)
MA_CORS=$($COMPOSE exec -T deal-mgmt-api env 2>/dev/null | grep -E "^ALLOWED_ORIGINS=" | cut -d= -f2- || echo "MISSING")
if echo "$MA_CORS" | grep -qP '^\['; then
  ok "deal-mgmt-api" "ALLOWED_ORIGINS=${MA_CORS:0:50}... (json)"
elif [ "$MA_CORS" != "MISSING" ]; then
  warn "deal-mgmt-api" "ALLOWED_ORIGINS 형식 비정상"
  SECTION_OK=false
else
  fail "deal-mgmt-api" "ALLOWED_ORIGINS 누락"
  SECTION_OK=false
fi

section_result "CORS Configuration" $SECTION_OK

# ============================================================
# [6/10] 헬스체크 엔드포인트
# ============================================================
echo -e "${CYAN}[6/10] Health Endpoints${NC}"
SECTION_OK=true

for mod in fdd kiis im ma; do
  RESPONSE=$(curl -sf --max-time 10 "http://localhost/api/$mod/health" 2>/dev/null || echo '{"status":"unreachable"}')
  STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "parse_error")
  MIGR=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('migration_ok','N/A'))" 2>/dev/null || echo "N/A")

  if [ "$STATUS" = "ok" ]; then
    if [ "$MIGR" = "False" ]; then
      fail "/api/$mod/health" "status=ok BUT migration_ok=false"
      SECTION_OK=false
      FAILURES+=("[6] Health: $mod migration_ok=false")
    else
      ok "/api/$mod/health" "200 status=$STATUS migration=$MIGR"
    fi
  else
    fail "/api/$mod/health" "status=$STATUS"
    SECTION_OK=false
    FAILURES+=("[6] Health: $mod 상태 비정상 ($STATUS)")
    FIXES+=("docker compose logs $mod-api --tail=50 로 로그 확인")
  fi
done

# 프론트엔드
FRONTEND=$(curl -sf --max-time 10 "http://localhost/" -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")
if [ "$FRONTEND" = "200" ]; then
  ok "/ (frontend)" "200"
else
  fail "/ (frontend)" "HTTP $FRONTEND"
  SECTION_OK=false
  FAILURES+=("[6] Health: 프론트엔드 응답 실패 (HTTP $FRONTEND)")
fi

section_result "Health Endpoints" $SECTION_OK

# ============================================================
# [7/10] 크로스 모듈 인증
# ============================================================
echo -e "${CYAN}[7/10] Cross-Module Auth${NC}"
SECTION_OK=true

# FDD 로그인
LOGIN_RESP=$(curl -sf --max-time 10 -X POST "http://localhost/api/fdd/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"jwsuh@amic.kr","password":"1111"}' 2>/dev/null || echo '{}')

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || echo "")

if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
  ok "FDD login" "토큰 획득 성공"

  # FDD /auth/me
  ME_STATUS=$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "http://localhost/api/fdd/auth/me" 2>/dev/null || echo "000")
  if [ "$ME_STATUS" = "200" ]; then
    ok "FDD /auth/me" "200"
  else
    fail "FDD /auth/me" "HTTP $ME_STATUS"
    SECTION_OK=false
  fi

  # MA /transactions
  MA_STATUS=$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "http://localhost/api/ma/transactions" 2>/dev/null || echo "000")
  if [ "$MA_STATUS" = "200" ]; then
    ok "MA /transactions" "200"
  else
    fail "MA /transactions" "HTTP $MA_STATUS"
    SECTION_OK=false
    FAILURES+=("[7] Auth: FDD JWT로 MA 접근 실패 (HTTP $MA_STATUS) — JWT_SECRET 불일치 가능")
  fi

  # KIIS (unread-count)
  KIIS_STATUS=$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "http://localhost/api/kiis/alerts/unread-count" 2>/dev/null || echo "000")
  if [ "$KIIS_STATUS" = "200" ]; then
    ok "KIIS /alerts" "200"
  else
    fail "KIIS /alerts" "HTTP $KIIS_STATUS"
    SECTION_OK=false
    FAILURES+=("[7] Auth: FDD JWT로 KIIS 접근 실패 (HTTP $KIIS_STATUS)")
  fi
else
  fail "FDD login" "로그인 실패 — 토큰 미획득"
  SECTION_OK=false
  FAILURES+=("[7] Auth: FDD 로그인 자체 실패 — DB 연결 또는 사용자 데이터 확인")
  warn "FDD /auth/me" "스킵 (토큰 없음)"
  warn "MA /transactions" "스킵 (토큰 없음)"
  warn "KIIS /alerts" "스킵 (토큰 없음)"
fi

section_result "Cross-Module Auth" $SECTION_OK

# ============================================================
# [8/10] Nginx & SSL
# ============================================================
echo -e "${CYAN}[8/10] Nginx & SSL${NC}"
SECTION_OK=true

# upstream 응답 (nginx 통해)
for mod in fdd kiis im ma; do
  HTTP_CODE=$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" \
    "http://localhost/api/$mod/health" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    ok "upstream $mod" "200"
  elif [ "$HTTP_CODE" = "502" ]; then
    fail "upstream $mod" "502 Bad Gateway — 컨테이너 미시작 또는 크래시"
    SECTION_OK=false
    FAILURES+=("[8] Nginx: $mod upstream 502 — 컨테이너 상태 확인")
  else
    fail "upstream $mod" "HTTP $HTTP_CODE"
    SECTION_OK=false
  fi
done

# 보안 헤더 (CSP, HSTS)
HEADERS=$(curl -sI --max-time 10 "http://localhost/" 2>/dev/null || echo "")
if echo "$HEADERS" | grep -qi "content-security-policy"; then
  CSP=$(echo "$HEADERS" | grep -i "content-security-policy" | head -1)
  ok "CSP header" "설정됨"
else
  warn "CSP header" "미설정"
fi

if echo "$HEADERS" | grep -qi "strict-transport-security"; then
  ok "HSTS header" "설정됨"
else
  warn "HSTS header" "미설정 (HTTP 전용 환경에서는 정상)"
fi

# SSL 인증서 만료일 (HTTPS 사용 시만)
SSL_EXPIRY=$(echo | openssl s_client -connect localhost:443 -servername localhost 2>/dev/null | openssl x509 -noout -dates 2>/dev/null | grep "notAfter" | cut -d= -f2)
if [ -n "$SSL_EXPIRY" ]; then
  EXPIRY_EPOCH=$(date -d "$SSL_EXPIRY" +%s 2>/dev/null || echo "0")
  NOW_EPOCH=$(date +%s)
  DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
  if [ "$DAYS_LEFT" -lt 14 ]; then
    fail "SSL cert" "만료 $DAYS_LEFT일 남음! ($SSL_EXPIRY)"
    SECTION_OK=false
    FAILURES+=("[8] SSL: 인증서 $DAYS_LEFT일 후 만료")
    FIXES+=("certbot renew --nginx")
  elif [ "$DAYS_LEFT" -lt 30 ]; then
    warn "SSL cert" "만료 $DAYS_LEFT일 남음 ($SSL_EXPIRY)"
  else
    ok "SSL cert" "만료 ${DAYS_LEFT}일 남음 ($SSL_EXPIRY)"
  fi
else
  warn "SSL cert" "HTTPS 미사용 또는 인증서 확인 불가"
fi

section_result "Nginx & SSL" $SECTION_OK

# ============================================================
# [9/10] Redis & Elasticsearch
# ============================================================
echo -e "${CYAN}[9/10] Redis & Elasticsearch${NC}"
SECTION_OK=true

# KIIS Redis
KIIS_REDIS=$($COMPOSE exec -T kiis-redis redis-cli -a "${KIIS_REDIS_PASSWORD:-redis}" ping 2>/dev/null | tr -d '[:space:]')
if [ "$KIIS_REDIS" = "PONG" ]; then
  ok "kiis-redis" "PONG"
else
  fail "kiis-redis" "PING 실패 ($KIIS_REDIS)"
  SECTION_OK=false
  FAILURES+=("[9] Redis: kiis-redis 연결 실패")
fi

# KIIS Elasticsearch
ES_HEALTH=$($COMPOSE exec -T kiis-es curl -sf --max-time 10 -u "elastic:${KIIS_ES_PASSWORD:-changeme}" "http://localhost:9200/_cluster/health?pretty" 2>/dev/null || echo '{}')
ES_STATUS=$(echo "$ES_HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
if [ "$ES_STATUS" = "green" ] || [ "$ES_STATUS" = "yellow" ]; then
  ok "kiis-es" "cluster=$ES_STATUS"
else
  fail "kiis-es" "cluster=$ES_STATUS"
  SECTION_OK=false
  FAILURES+=("[9] ES: kiis-es 클러스터 상태 $ES_STATUS")
fi

# IM Redis
IM_REDIS=$($COMPOSE exec -T im-redis redis-cli -a "${IM_REDIS_PASSWORD:-redis}" ping 2>/dev/null | tr -d '[:space:]')
if [ "$IM_REDIS" = "PONG" ]; then
  ok "im-redis" "PONG"
else
  fail "im-redis" "PING 실패"
  SECTION_OK=false
  FAILURES+=("[9] Redis: im-redis 연결 실패")
fi

# IM Celery Worker
CELERY_STATUS=$($COMPOSE exec -T im-celery-worker celery -A src.api.tasks.celery_app inspect ping 2>/dev/null || echo "")
if echo "$CELERY_STATUS" | grep -q "pong"; then
  WORKER_COUNT=$(echo "$CELERY_STATUS" | grep -c "pong")
  ok "im-celery" "$WORKER_COUNT worker(s) online"
else
  fail "im-celery" "워커 응답 없음"
  SECTION_OK=false
  FAILURES+=("[9] Celery: im-celery-worker 응답 없음")
fi

section_result "Redis & Elasticsearch" $SECTION_OK

# ============================================================
# [10/10] 디스크 & 리소스
# ============================================================
echo -e "${CYAN}[10/10] Disk & Resources${NC}"
SECTION_OK=true

# 디스크 사용량
DISK_USAGE=$(df -h / 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
DISK_TOTAL=$(df -h / 2>/dev/null | tail -1 | awk '{print $2}')
DISK_USED=$(df -h / 2>/dev/null | tail -1 | awk '{print $3}')
if [ -n "$DISK_USAGE" ]; then
  if [ "$DISK_USAGE" -gt 90 ]; then
    fail "Disk" "${DISK_USAGE}% 사용 (${DISK_USED}/${DISK_TOTAL})"
    SECTION_OK=false
    FAILURES+=("[10] Disk: 사용량 ${DISK_USAGE}% — 90% 초과!")
    FIXES+=("docker system prune -f && docker volume prune -f")
  elif [ "$DISK_USAGE" -gt 80 ]; then
    warn "Disk" "${DISK_USAGE}% 사용 (${DISK_USED}/${DISK_TOTAL})"
  else
    ok "Disk" "${DISK_USAGE}% 사용 (${DISK_USED}/${DISK_TOTAL})"
  fi
fi

# 메모리
MEM_INFO=$(free -h 2>/dev/null | grep "Mem:" | awk '{print $3"/"$2" ("$3/$2*100"%)"}' || echo "unknown")
MEM_PCT=$(free 2>/dev/null | grep "Mem:" | awk '{printf "%.0f", $3/$2*100}' || echo "0")
if [ "$MEM_PCT" -gt 90 ]; then
  fail "Memory" "$MEM_INFO"
  SECTION_OK=false
  FAILURES+=("[10] Memory: 사용량 ${MEM_PCT}% — 90% 초과!")
elif [ "$MEM_PCT" -gt 80 ]; then
  warn "Memory" "$MEM_INFO"
else
  ok "Memory" "$MEM_INFO"
fi

# Docker 볼륨
VOL_COUNT=$(docker volume ls -q 2>/dev/null | wc -l)
ok "Docker volumes" "$VOL_COUNT 개"

section_result "Disk & Resources" $SECTION_OK

# ============================================================
# 최종 결과
# ============================================================
TOTAL=$((PASS_COUNT + FAIL_COUNT))
echo -e "${BOLD}════════════════════════════════════════════════${NC}"
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo -e "  ${GREEN}${BOLD}OVERALL: $PASS_COUNT/$TOTAL PASSED ✓${NC}"
  echo -e "  이상 없음."
else
  echo -e "  ${RED}${BOLD}OVERALL: $PASS_COUNT/$TOTAL PASSED, $FAIL_COUNT FAILED ✗${NC}"
  echo ""
  echo -e "  ${RED}FAILURES:${NC}"
  for f in "${FAILURES[@]}"; do
    echo -e "  ${RED}→${NC} $f"
  done
  echo ""
  echo -e "  ${YELLOW}SUGGESTED FIXES:${NC}"
  for fx in "${FIXES[@]}"; do
    echo -e "  ${YELLOW}$${NC} $fx"
  done
fi
echo -e "${BOLD}════════════════════════════════════════════════${NC}"
echo ""

# CI 모드에서 실패 시 exit 1
if $CI_MODE && [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi

exit 0
