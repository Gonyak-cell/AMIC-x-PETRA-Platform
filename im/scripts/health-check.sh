#!/bin/bash
set -e

# API 헬스체크 스크립트
# 사용법: ./scripts/health-check.sh [url]

# API URL (기본값: localhost)
API_URL=${1:-"http://localhost:8000"}

echo "=== API 헬스체크 ==="
echo "대상 URL: $API_URL"
echo ""

# 헬스체크 엔드포인트 확인
echo "1. 기본 헬스체크 (/health)..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health" || echo "000")

if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo "✓ /health: OK (HTTP $HEALTH_RESPONSE)"
    HEALTH_OK=true
else
    echo "✗ /health: FAILED (HTTP $HEALTH_RESPONSE)"
    HEALTH_OK=false
fi

# Readiness 엔드포인트 확인
echo "2. Readiness 체크 (/ready)..."
READY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/ready" || echo "000")

if [ "$READY_RESPONSE" = "200" ]; then
    echo "✓ /ready: OK (HTTP $READY_RESPONSE)"
    READY_OK=true
else
    echo "✗ /ready: FAILED (HTTP $READY_RESPONSE)"
    READY_OK=false
fi

# 상세 정보 가져오기 (가능한 경우)
echo ""
echo "=== 상세 정보 ==="

if [ "$HEALTH_OK" = true ]; then
    echo "헬스 정보:"
    curl -s "$API_URL/health" | python3 -m json.tool 2>/dev/null || echo "JSON 파싱 실패"
fi

if [ "$READY_OK" = true ]; then
    echo ""
    echo "Readiness 정보:"
    curl -s "$API_URL/ready" | python3 -m json.tool 2>/dev/null || echo "JSON 파싱 실패"
fi

# 최종 결과
echo ""
echo "=== 최종 결과 ==="

if [ "$HEALTH_OK" = true ] && [ "$READY_OK" = true ]; then
    echo "✓ 모든 헬스체크 통과"
    exit 0
elif [ "$HEALTH_OK" = true ]; then
    echo "⚠ 헬스체크는 통과했으나 Readiness 실패"
    echo "  서비스가 아직 준비되지 않았습니다 (DB, Redis 등 확인)"
    exit 1
else
    echo "✗ 헬스체크 실패"
    echo "  서비스가 실행 중이지 않거나 응답하지 않습니다"
    exit 2
fi
