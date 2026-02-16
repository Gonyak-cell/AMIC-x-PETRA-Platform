#!/bin/bash
set -e

# Let's Encrypt SSL 인증서 초기화 스크립트
# 사용법: ./scripts/init-letsencrypt.sh <domain> <email>

echo "=== Let's Encrypt SSL 인증서 초기화 ==="

# 인자 확인
if [ $# -ne 2 ]; then
    echo "사용법: $0 <domain> <email>"
    echo "예제: $0 api.example.com admin@example.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2

echo "도메인: $DOMAIN"
echo "이메일: $EMAIL"

# 필요한 디렉토리 생성
echo "필요한 디렉토리 생성 중..."
mkdir -p ./certbot/conf
mkdir -p ./certbot/www
mkdir -p ./certbot/logs

# 기존 인증서 확인
if [ -d "./certbot/conf/live/$DOMAIN" ]; then
    echo "경고: $DOMAIN 에 대한 기존 인증서가 발견되었습니다."
    read -p "기존 인증서를 삭제하고 새로 발급받으시겠습니까? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "작업이 취소되었습니다."
        exit 0
    fi
    echo "기존 인증서 삭제 중..."
    rm -rf "./certbot/conf/live/$DOMAIN"
    rm -rf "./certbot/conf/archive/$DOMAIN"
    rm -rf "./certbot/conf/renewal/$DOMAIN.conf"
fi

# Nginx 컨테이너 시작 (HTTP만, Let's Encrypt 챌린지용)
echo "Nginx 컨테이너 시작 중 (HTTP 모드)..."
docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d nginx

# Let's Encrypt 인증서 발급 요청
echo "Let's Encrypt 인증서 발급 요청 중..."
docker-compose -f docker-compose.yml -f docker-compose.production.yml run --rm certbot \
    certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$DOMAIN"

if [ $? -eq 0 ]; then
    echo "✓ SSL 인증서가 성공적으로 발급되었습니다."
    echo "  위치: ./certbot/conf/live/$DOMAIN/"

    # Nginx 재시작 (HTTPS 모드)
    echo "Nginx 재시작 중 (HTTPS 모드)..."
    docker-compose -f docker-compose.yml -f docker-compose.production.yml restart nginx

    echo "✓ 완료! HTTPS가 활성화되었습니다."
    echo "  URL: https://$DOMAIN"
else
    echo "✗ 인증서 발급 실패!"
    echo "다음을 확인해주세요:"
    echo "  1. 도메인이 이 서버의 IP를 가리키고 있는지 확인"
    echo "  2. 80 포트가 열려있고 접근 가능한지 확인"
    echo "  3. 방화벽 설정 확인"
    exit 1
fi
