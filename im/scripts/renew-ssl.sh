#!/bin/bash
set -e

# Let's Encrypt SSL 인증서 갱신 스크립트
# Cron으로 실행: 0 0 * * * /path/to/renew-ssl.sh

echo "=== Let's Encrypt SSL 인증서 갱신 ==="
echo "시작 시간: $(date)"

# 프로젝트 루트 디렉토리로 이동
cd "$(dirname "$0")/.."

# Certbot으로 인증서 갱신 시도
echo "인증서 갱신 시도 중..."
docker-compose -f docker-compose.yml -f docker-compose.production.yml run --rm certbot renew

if [ $? -eq 0 ]; then
    echo "✓ 인증서 갱신 확인 완료"

    # Nginx 재시작 (갱신된 인증서 적용)
    echo "Nginx 재시작 중..."
    docker-compose -f docker-compose.yml -f docker-compose.production.yml restart nginx

    if [ $? -eq 0 ]; then
        echo "✓ Nginx 재시작 완료"
        echo "✓ SSL 인증서 갱신 프로세스 완료"
    else
        echo "✗ Nginx 재시작 실패!"
        exit 1
    fi
else
    echo "✗ 인증서 갱신 실패!"
    echo "인증서가 아직 만료되지 않았거나 갱신이 필요하지 않을 수 있습니다."
    echo "인증서는 만료 30일 전부터 갱신 가능합니다."
fi

echo "종료 시간: $(date)"
