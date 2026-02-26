#!/bin/bash
set -e

echo "=== Deal Management Docker Entrypoint ==="
# 마이그레이션은 deploy.yml에서 관리 (중복 실행 방지)
echo "Starting Deal Management application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-2}
