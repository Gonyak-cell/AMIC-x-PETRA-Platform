# Auto FDD — 베타 배포 가이드

> 작성: Sprint 12 Phase 4

---

## 1. 사전 조건

| 항목 | 요구사항 |
|------|----------|
| Docker | v24+ |
| Docker Compose | v2.20+ |
| PostgreSQL | 16+ |
| Node.js | 20+ (pptx-service) |
| Python | 3.12+ |
| 도메인 | HTTPS 인증서 필요 |

---

## 2. 환경 변수

```bash
# .env.production
DATABASE_URL=postgresql://fdd_user:<PASSWORD>@db:5432/fdd_prod
AUTH_ENABLED=true
JWT_SECRET=<32자 이상 랜덤 시크릿>
JWT_EXPIRY_MINUTES=60
JWT_REFRESH_EXPIRY_DAYS=7
UPLOAD_DIR=/data/uploads
CORS_ORIGINS=https://fdd.example.com
LOG_LEVEL=INFO
PPTX_SERVICE_URL=http://pptx:3100
```

> **주의**: `.env` 파일은 절대 Git에 커밋하지 마세요. AWS Secrets Manager 또는 GCP Secret Manager 사용 권장.

---

## 3. 배포 절차

### 3.1 Docker Compose (단일 서버)

```bash
# 1. 환경 변수 설정
cp .env.example .env.production
# .env.production 편집

# 2. 이미지 빌드
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# 3. DB 마이그레이션
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  run --rm backend alembic upgrade head

# 4. 서비스 시작
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 5. 헬스 체크
curl -f http://localhost:8000/health
curl -f http://localhost:5173
curl -f http://localhost:3100/health
```

### 3.2 초기 사용자 생성

```bash
docker compose exec backend python -c "
from app.auth.password import hash_password
from app.models.user import User, UserRole
from app.database import SessionLocal

db = SessionLocal()
admin = User(
    email='admin@company.com',
    hashed_password=hash_password('초기비밀번호변경필수'),
    display_name='Admin',
    role=UserRole.ADMIN,
)
db.add(admin)
db.commit()
print(f'Created admin user: {admin.id}')
db.close()
"
```

---

## 4. HTTPS 설정

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name fdd.example.com;

    ssl_certificate /etc/letsencrypt/live/fdd.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fdd.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 100M;
    }
}
```

---

## 5. 모니터링

| 엔드포인트 | 용도 |
|-----------|------|
| `GET /health` | 헬스 체크 |
| `GET /metrics` | Prometheus 메트릭 |
| `GET /metrics/json` | JSON 메트릭 |

### Prometheus scrape 설정

```yaml
scrape_configs:
  - job_name: 'autofdd-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /metrics
```

---

## 6. 백업

```bash
# PostgreSQL 백업 (매일)
pg_dump -U fdd_user -h db fdd_prod | gzip > /backups/fdd_$(date +%Y%m%d).sql.gz

# 업로드 파일 백업
tar czf /backups/uploads_$(date +%Y%m%d).tar.gz /data/uploads/
```

---

## 7. 배포 체크리스트

- [ ] `.env.production` 설정 완료
- [ ] JWT_SECRET 32자 이상 랜덤 값
- [ ] HTTPS 인증서 설정
- [ ] DB 마이그레이션 실행
- [ ] 초기 Admin 사용자 생성
- [ ] 헬스 체크 통과
- [ ] 모니터링 대시보드 연결
- [ ] 백업 스케줄 설정
- [ ] 로그 수집 설정
