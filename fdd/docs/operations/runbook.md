# Auto FDD — 운영 Runbook

> 작성: Sprint 12 Phase 4

---

## 1. 일상 운영

### 1.1 헬스 체크

```bash
# 전체 서비스 상태
curl http://localhost:8000/health
curl http://localhost:5173
curl http://localhost:3100/health

# Docker 컨테이너 상태
docker compose ps
```

### 1.2 로그 확인

```bash
# 전체 로그
docker compose logs --tail=100

# 서비스별 로그
docker compose logs backend --tail=50
docker compose logs frontend --tail=50
docker compose logs pptx --tail=50
docker compose logs db --tail=50

# 실시간 로그 스트림
docker compose logs -f backend
```

### 1.3 메트릭 확인

```bash
# Prometheus 메트릭
curl http://localhost:8000/metrics

# JSON 메트릭
curl http://localhost:8000/metrics/json | python -m json.tool
```

---

## 2. 장애 대응

### 2.1 Backend 503 (DB 연결 실패)

```bash
# DB 상태 확인
docker compose exec db pg_isready

# DB 컨테이너 재시작
docker compose restart db
sleep 10

# Backend 재시작
docker compose restart backend

# 헬스 체크
curl http://localhost:8000/health
```

### 2.2 PPT 생성 실패 (pptx-service)

```bash
# pptx-service 로그 확인
docker compose logs pptx --tail=30

# 재시작
docker compose restart pptx

# 헬스 체크
curl http://localhost:3100/health
```

### 2.3 디스크 부족

```bash
# 디스크 사용량 확인
df -h
du -sh /data/uploads/

# 오래된 업로드 파일 정리 (30일 이상)
find /data/uploads -type f -mtime +30 -delete

# Docker 이미지/볼륨 정리
docker system prune -f
```

### 2.4 메모리 부족 (OOM)

```bash
# 메모리 사용량 확인
docker stats --no-stream

# 가장 많이 사용하는 컨테이너 재시작
docker compose restart <service>
```

---

## 3. 데이터 관리

### 3.1 감사 로그 정리

```bash
# 만료된 감사 로그 확인 (dry run)
curl -X POST "http://localhost:8000/api/v1/retention/purge/audit-logs?dry_run=true" \
  -H "Authorization: Bearer <admin_token>"

# 실제 삭제
curl -X POST "http://localhost:8000/api/v1/retention/purge/audit-logs?dry_run=false" \
  -H "Authorization: Bearer <admin_token>"
```

### 3.2 사용자 관리

```bash
# 사용자 목록
curl "http://localhost:8000/api/v1/auth/users" \
  -H "Authorization: Bearer <admin_token>"

# 사용자 추가
curl -X POST "http://localhost:8000/api/v1/auth/users" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"new@company.com","password":"초기비밀번호","display_name":"신규사용자"}'
```

---

## 4. 성능 모니터링 SLA

| 지표 | 임계값 | 알림 |
|------|--------|------|
| API 응답 시간 (p95) | < 2초 | WARNING |
| API 응답 시간 (p99) | < 5초 | CRITICAL |
| 에러율 | < 1% | WARNING |
| 에러율 | > 5% | CRITICAL |
| DB 커넥션 풀 | < 80% | WARNING |
| 디스크 사용률 | > 80% | WARNING |
| 메모리 사용률 | > 85% | WARNING |

---

## 5. 비상 연락처

| 역할 | 담당 | 연락처 |
|------|------|--------|
| 시스템 관리자 | TBD | - |
| DB 관리자 | TBD | - |
| 개발 리드 | TBD | - |
