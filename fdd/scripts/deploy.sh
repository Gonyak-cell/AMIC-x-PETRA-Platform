#!/usr/bin/env bash
# Auto FDD — Production Deployment Script
# Usage: ./scripts/deploy.sh [up|down|restart|status|migrate|backup|logs|benchmark]
# SSL:   SSL_ENABLED=true ./scripts/deploy.sh up

set -euo pipefail

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
ENV_FILE=".env.production"

# SSL support: append SSL compose if enabled
if [ -f "$ENV_FILE" ]; then
    SSL_ENABLED=$(grep -oP 'SSL_ENABLED=\K.*' "$ENV_FILE" 2>/dev/null || echo "false")
    if [ "$SSL_ENABLED" = "true" ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.ssl.yml"
    fi
fi

# ── Color helpers ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[DEPLOY]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Pre-checks ──
check_env() {
    if [ ! -f "$ENV_FILE" ]; then
        err "$ENV_FILE not found. Copy .env.production.example and fill in values."
        exit 1
    fi

    # JWT_SECRET 길이 확인
    JWT=$(grep -oP 'JWT_SECRET=\K.*' "$ENV_FILE" || true)
    if [ ${#JWT} -lt 32 ]; then
        err "JWT_SECRET must be at least 32 characters."
        exit 1
    fi

    # 기본 비밀번호 사용 여부
    if grep -q "CHANGE_ME" "$ENV_FILE"; then
        err "Found CHANGE_ME placeholder in $ENV_FILE. Update all values."
        exit 1
    fi

    log "Environment check passed."
}

check_docker() {
    if ! command -v docker &>/dev/null; then
        err "Docker not found. Install Docker 24+."
        exit 1
    fi
    if ! docker compose version &>/dev/null; then
        err "Docker Compose v2 not found."
        exit 1
    fi
    log "Docker $(docker --version | grep -oP '\d+\.\d+\.\d+')"
}

# ── Commands ──
cmd_up() {
    check_env
    check_docker

    log "Building images..."
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" build

    log "Running DB migrations..."
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" \
        run --rm backend alembic upgrade head

    log "Starting services..."
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" up -d

    log "Waiting for health checks..."
    sleep 10
    cmd_health
}

cmd_down() {
    log "Stopping services..."
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" down
    log "All services stopped."
}

cmd_restart() {
    log "Restarting services..."
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" restart
    sleep 5
    cmd_health
}

cmd_status() {
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" ps
}

cmd_migrate() {
    log "Running DB migrations..."
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" \
        run --rm backend alembic upgrade head
    log "Migrations complete."
}

cmd_backup() {
    BACKUP_DIR="${BACKUP_DIR:-./backups}"
    mkdir -p "$BACKUP_DIR"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)

    log "Backing up database..."
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" \
        exec -T db pg_dump -U "${POSTGRES_USER:-fdd_user}" "${POSTGRES_DB:-fdd_prod}" \
        | gzip > "$BACKUP_DIR/fdd_${TIMESTAMP}.sql.gz"

    log "Backing up uploads..."
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" \
        exec -T backend tar czf - /data/uploads 2>/dev/null \
        > "$BACKUP_DIR/uploads_${TIMESTAMP}.tar.gz" || true

    log "Backup complete: $BACKUP_DIR/fdd_${TIMESTAMP}.sql.gz"
    ls -lh "$BACKUP_DIR"/fdd_${TIMESTAMP}* "$BACKUP_DIR"/uploads_${TIMESTAMP}* 2>/dev/null
}

cmd_logs() {
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" logs -f --tail=100
}

cmd_health() {
    local ok=true

    # Backend
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log "Backend:  OK"
    else
        warn "Backend:  UNREACHABLE"
        ok=false
    fi

    # Frontend
    if curl -sf http://localhost:80/ > /dev/null 2>&1; then
        log "Frontend: OK"
    else
        warn "Frontend: UNREACHABLE"
        ok=false
    fi

    # PPTX Service
    if curl -sf http://localhost:3100/health > /dev/null 2>&1; then
        log "PPTX:     OK"
    else
        warn "PPTX:     UNREACHABLE"
        ok=false
    fi

    if [ "$ok" = false ]; then
        warn "Some services are not healthy. Check logs: ./scripts/deploy.sh logs"
        return 1
    fi
    log "All services healthy."
}

cmd_create_admin() {
    read -p "Admin email: " ADMIN_EMAIL
    read -sp "Admin password: " ADMIN_PASS
    echo

    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" \
        exec backend python -c "
from app.auth.password import hash_password
from app.models.user import User, UserRole
from app.database import SessionLocal

db = SessionLocal()
admin = User(
    email='${ADMIN_EMAIL}',
    hashed_password=hash_password('${ADMIN_PASS}'),
    display_name='Admin',
    role=UserRole.ADMIN,
)
db.add(admin)
db.commit()
print(f'Created admin user: {admin.id}')
db.close()
"
    log "Admin user created: $ADMIN_EMAIL"
}

# ── Main ──
case "${1:-help}" in
    up)           cmd_up ;;
    down)         cmd_down ;;
    restart)      cmd_restart ;;
    status)       cmd_status ;;
    migrate)      cmd_migrate ;;
    backup)       cmd_backup ;;
    logs)         cmd_logs ;;
    health)       cmd_health ;;
    create-admin) cmd_create_admin ;;
    benchmark)
        log "Running performance benchmarks..."
        python scripts/performance_benchmark.py --target all --output-dir docs/benchmarks
        ;;
    monitoring)
        log "Starting monitoring stack..."
        docker compose -f docker-compose.monitoring.yml --env-file "$ENV_FILE" up -d
        log "Grafana: http://localhost:3000  Prometheus: http://localhost:9090"
        ;;
    sample-data)
        log "Generating sample data for beta pilot..."
        python scripts/generate-sample-data.py --output-dir data/samples
        ;;
    *)
        echo "Auto FDD — Deploy Script"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  up           Build, migrate, and start all services"
        echo "  down         Stop all services"
        echo "  restart      Restart all services"
        echo "  status       Show service status"
        echo "  migrate      Run database migrations"
        echo "  backup       Backup database and uploads"
        echo "  logs         Tail service logs"
        echo "  health       Check service health"
        echo "  create-admin Create initial admin user"
        echo "  benchmark    Run performance benchmarks"
        echo "  monitoring   Start Prometheus + Grafana stack"
        echo "  sample-data  Generate sample TB/GL for beta pilot"
        echo ""
        echo "SSL: Set SSL_ENABLED=true in .env.production to enable HTTPS"
        ;;
esac
