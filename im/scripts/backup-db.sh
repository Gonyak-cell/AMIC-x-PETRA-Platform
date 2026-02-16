#!/bin/bash
set -e

# 데이터베이스 백업 스크립트
# Cron으로 실행: 0 2 * * * /path/to/backup-db.sh

echo "=== 데이터베이스 백업 ==="
echo "시작 시간: $(date)"

# 프로젝트 루트 디렉토리로 이동
cd "$(dirname "$0")/.."

# 백업 디렉토리 생성
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

# 백업 파일명 (날짜 포함)
BACKUP_FILE="$BACKUP_DIR/db-backup-$(date +%Y%m%d-%H%M%S).sql.gz"

# Docker Compose에서 DB 컨테이너 이름 가져오기
DB_CONTAINER=$(docker-compose ps -q db)

if [ -z "$DB_CONTAINER" ]; then
    echo "✗ DB 컨테이너를 찾을 수 없습니다."
    echo "docker-compose가 실행 중인지 확인하세요."
    exit 1
fi

# 환경변수 로드 (.env 파일에서)
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "✗ .env 파일을 찾을 수 없습니다."
    exit 1
fi

# PostgreSQL 덤프 수행 및 압축
echo "데이터베이스 백업 중..."
docker exec "$DB_CONTAINER" pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-auto_im_generator}" | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ 백업 완료: $BACKUP_FILE ($BACKUP_SIZE)"

    # 7일 이상 된 백업 파일 삭제
    echo "오래된 백업 파일 정리 중 (7일 이상)..."
    find "$BACKUP_DIR" -name "db-backup-*.sql.gz" -mtime +7 -delete
    echo "✓ 정리 완료"

    # 현재 백업 파일 목록
    echo "현재 백업 파일 목록:"
    ls -lh "$BACKUP_DIR"/db-backup-*.sql.gz
else
    echo "✗ 백업 실패!"
    exit 1
fi

echo "종료 시간: $(date)"
