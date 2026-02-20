#!/bin/bash
# ============================================================
# AMIC x PETRA Platform — 전체 DB 백업 스크립트
# ============================================================
# 사용법: bash scripts/backup-all-dbs.sh
# cron:   0 2 * * * /path/to/scripts/backup-all-dbs.sh >> /var/log/db-backup.log 2>&1
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups/$(date +%Y%m%d-%H%M%S)"
RETENTION_DAYS=7

echo "=== AMIC x PETRA Platform — DB Backup ==="
echo "시작: $(date '+%Y-%m-%d %H:%M:%S')"
echo "백업 경로: $BACKUP_DIR"

mkdir -p "$BACKUP_DIR"

FAILED=0

# FDD
echo -n "  [1/4] FDD..."
if docker exec amic-fdd-db pg_dump -U autofdd autofdd 2>/dev/null | gzip > "$BACKUP_DIR/fdd.sql.gz"; then
  echo " OK ($(du -h "$BACKUP_DIR/fdd.sql.gz" | cut -f1))"
else
  echo " FAILED"
  FAILED=$((FAILED + 1))
fi

# KIIS
echo -n "  [2/4] KIIS..."
if docker exec amic-kiis-db pg_dump -U kiis_user kiis 2>/dev/null | gzip > "$BACKUP_DIR/kiis.sql.gz"; then
  echo " OK ($(du -h "$BACKUP_DIR/kiis.sql.gz" | cut -f1))"
else
  echo " FAILED"
  FAILED=$((FAILED + 1))
fi

# IM
echo -n "  [3/4] IM..."
if docker exec amic-im-db pg_dump -U postgres imgen 2>/dev/null | gzip > "$BACKUP_DIR/im.sql.gz"; then
  echo " OK ($(du -h "$BACKUP_DIR/im.sql.gz" | cut -f1))"
else
  echo " FAILED"
  FAILED=$((FAILED + 1))
fi

# Deal Management
echo -n "  [4/4] MA..."
if docker exec amic-deal-mgmt-db pg_dump -U deal_mgmt_user deal_mgmt 2>/dev/null | gzip > "$BACKUP_DIR/deal-mgmt.sql.gz"; then
  echo " OK ($(du -h "$BACKUP_DIR/deal-mgmt.sql.gz" | cut -f1))"
else
  echo " FAILED"
  FAILED=$((FAILED + 1))
fi

# 총 백업 크기
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
echo ""
echo "총 크기: $TOTAL_SIZE"

# 오래된 백업 정리
DELETED=$(find "$PROJECT_ROOT/backups" -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" 2>/dev/null | wc -l)
if [ "$DELETED" -gt 0 ]; then
  find "$PROJECT_ROOT/backups" -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} + 2>/dev/null
  echo "정리: ${RETENTION_DAYS}일 이전 백업 ${DELETED}개 삭제"
fi

echo "종료: $(date '+%Y-%m-%d %H:%M:%S')"

if [ "$FAILED" -gt 0 ]; then
  echo "WARNING: $FAILED/4 백업 실패"
  exit 1
fi

echo "=== 백업 완료 ==="
