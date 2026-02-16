#!/bin/bash
set -e

# 로컬 개발용 자체 서명 SSL 인증서 생성 스크립트
# 사용법: ./scripts/generate-self-signed.sh [domain]

echo "=== 자체 서명 SSL 인증서 생성 (개발용) ==="

# 도메인 설정 (기본값: localhost)
DOMAIN=${1:-localhost}
echo "도메인: $DOMAIN"

# 출력 디렉토리 생성
CERT_DIR="./certbot/conf/live/$DOMAIN"
mkdir -p "$CERT_DIR"

# 자체 서명 인증서 생성
echo "자체 서명 인증서 생성 중..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/privkey.pem" \
    -out "$CERT_DIR/fullchain.pem" \
    -subj "/C=KR/ST=Seoul/L=Seoul/O=Development/OU=IT/CN=$DOMAIN"

if [ $? -eq 0 ]; then
    echo "✓ 자체 서명 인증서가 생성되었습니다."
    echo "  위치: $CERT_DIR/"
    echo "  - privkey.pem: 개인 키"
    echo "  - fullchain.pem: 인증서"
    echo ""
    echo "⚠ 경고: 이 인증서는 개발 목적으로만 사용하세요."
    echo "  프로덕션 환경에서는 Let's Encrypt를 사용하세요."
    echo "  (./scripts/init-letsencrypt.sh 참조)"
else
    echo "✗ 인증서 생성 실패!"
    exit 1
fi
