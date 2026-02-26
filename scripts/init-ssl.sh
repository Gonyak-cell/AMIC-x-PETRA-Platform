#!/bin/bash
# ============================================================
# AMIC x PETRA Platform — Let's Encrypt 최초 SSL 인증서 발급
# ============================================================
# 사용법: bash scripts/init-ssl.sh
#
# 사전 조건:
#   - DNS A 레코드: ap-platform.kr → 52.231.69.38
#   - 서버에서 80 포트 열려 있어야 함
#   - docker, docker compose 설치 완료
# ============================================================

set -euo pipefail

DOMAIN="ap-platform.kr"
EMAIL="dieding88@naver.com"

echo "=== Step 1: HTTP-only nginx 시작 (ACME 챌린지용) ==="
# prod-nossl.conf로 먼저 기동 (SSL 없이 80만)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d nginx

echo "=== Step 2: certbot으로 인증서 발급 ==="
docker run --rm \
  -v "$(docker volume inspect --format '{{.Mountpoint}}' "$(basename $(pwd))_certbot-etc" 2>/dev/null || echo certbot-etc):/etc/letsencrypt" \
  -v "$(docker volume inspect --format '{{.Mountpoint}}' "$(basename $(pwd))_certbot-var" 2>/dev/null || echo certbot-var):/var/lib/letsencrypt" \
  -v "$(docker volume inspect --format '{{.Mountpoint}}' "$(basename $(pwd))_certbot-www" 2>/dev/null || echo certbot-www):/var/www/certbot" \
  certbot/certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d "$DOMAIN" \
  -d "www.$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  --force-renewal

echo "=== Step 3: SSL 모드로 재기동 ==="
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.ssl.yml up -d

echo ""
echo "✅ SSL 설정 완료!"
echo "   https://$DOMAIN 에서 확인하세요."
