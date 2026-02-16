# Auto FDD — 롤백 절차

> 작성: Sprint 12 Phase 4

---

## 1. 롤백 판단 기준

| 상황 | 조치 |
|------|------|
| 헬스 체크 실패 (5분 이상) | 즉시 롤백 |
| API 에러율 > 5% | 즉시 롤백 |
| 데이터 손실 감지 | 즉시 롤백 + DB 복원 |
| UI 렌더링 불가 | 프론트엔드만 롤백 |
| 성능 저하 (SLA 200% 초과) | 1시간 모니터링 후 판단 |

---

## 2. Docker Compose 롤백

### 2.1 이전 버전으로 롤백

```bash
# 현재 버전 확인
docker compose ps

# 서비스 중지
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# 이전 태그로 변경
git checkout <previous-tag>

# 이미지 재빌드 및 시작
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 2.2 DB 마이그레이션 롤백

```bash
# 현재 마이그레이션 확인
docker compose exec backend alembic current

# 한 단계 롤백
docker compose exec backend alembic downgrade -1

# 특정 버전으로 롤백
docker compose exec backend alembic downgrade <revision_id>

# 마이그레이션 히스토리 확인
docker compose exec backend alembic history
```

### 2.3 DB 백업에서 복원

```bash
# 서비스 중지
docker compose stop backend pptx frontend

# DB 복원
gunzip < /backups/fdd_20260208.sql.gz | \
  docker compose exec -T db psql -U fdd_user fdd_prod

# 서비스 재시작
docker compose start backend pptx frontend

# 데이터 무결성 확인
curl -f http://localhost:8000/health
```

---

## 3. 롤백 후 확인사항

- [ ] 헬스 체크 통과: `GET /health` → 200
- [ ] API 응답 정상: `GET /api/v1/deals` → 200
- [ ] 프론트엔드 접근 가능
- [ ] 기존 데이터 무결성 확인
- [ ] 모니터링 대시보드 정상화
- [ ] 팀에 롤백 사실 공유

---

## 4. 롤백 이력 기록

| 날짜 | 버전 | 원인 | 조치 | 소요시간 |
|------|------|------|------|----------|
| - | - | - | - | - |
