#!/usr/bin/env bash
# Auto FDD — SSL Certificate Setup
# Usage:
#   ./scripts/setup-ssl.sh --domain fdd.example.com --email admin@example.com
#   ./scripts/setup-ssl.sh --self-signed --domain fdd.example.com

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[SSL]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

DOMAIN=""
EMAIL=""
SELF_SIGNED=false
CERT_DIR="./config/ssl"

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain) DOMAIN="$2"; shift 2 ;;
        --email) EMAIL="$2"; shift 2 ;;
        --self-signed) SELF_SIGNED=true; shift ;;
        *) err "Unknown arg: $1"; exit 1 ;;
    esac
done

if [ -z "$DOMAIN" ]; then
    err "Usage: $0 --domain <domain> [--email <email>] [--self-signed]"
    exit 1
fi

mkdir -p "$CERT_DIR"

if [ "$SELF_SIGNED" = true ]; then
    # ── Self-Signed Certificate ──
    log "Generating self-signed certificate for $DOMAIN..."

    mkdir -p "$CERT_DIR/certs" "$CERT_DIR/private"

    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout "$CERT_DIR/private/privkey.pem" \
        -out "$CERT_DIR/certs/fullchain.pem" \
        -subj "/CN=$DOMAIN/O=Auto FDD/C=KR" \
        2>/dev/null

    log "Self-signed certificate created:"
    log "  Certificate: $CERT_DIR/certs/fullchain.pem"
    log "  Private Key: $CERT_DIR/private/privkey.pem"
    warn "Self-signed certificates will show browser warnings."
    warn "Use Let's Encrypt for production."

else
    # ── Let's Encrypt (certbot) ──
    if [ -z "$EMAIL" ]; then
        err "--email is required for Let's Encrypt"
        exit 1
    fi

    if ! command -v certbot &>/dev/null; then
        log "Installing certbot..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get update && sudo apt-get install -y certbot
        elif command -v yum &>/dev/null; then
            sudo yum install -y certbot
        else
            err "Cannot install certbot automatically. Install manually."
            exit 1
        fi
    fi

    log "Requesting Let's Encrypt certificate for $DOMAIN..."

    # Create webroot directory for ACME challenge
    mkdir -p ./config/certbot/www

    certbot certonly \
        --webroot \
        --webroot-path=./config/certbot/www \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive

    # Copy certificates to our config directory
    mkdir -p "$CERT_DIR/certs" "$CERT_DIR/private"
    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$CERT_DIR/certs/"
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$CERT_DIR/private/"

    log "Let's Encrypt certificate obtained!"
    log "Certificate auto-renews via certbot timer."
fi

# ── Print next steps ──
log ""
log "Next steps:"
log "  1. Set SSL_ENABLED=true in .env.production"
log "  2. Set SSL_DOMAIN=$DOMAIN in .env.production"
log "  3. Restart: ./scripts/deploy.sh restart"
log ""
log "To verify: curl -k https://$DOMAIN/health"
