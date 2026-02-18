---
paths:
  - "fdd/**/*.py"
  - "kiis/**/*.py"
  - "im/**/*.py"
  - "docker-compose*.yml"
  - "nginx/**"
---
# Security Checklist (보안 규칙)

## CRITICAL: 시크릿 노출 방지
- **NEVER** commit `.env`, `credentials.json`, API keys, tokens to git
- `.gitignore`에 반드시 포함: `.env`, `.env.*`, `*.pem`, `*.key`, `credentials*`
- 환경변수는 `os.environ["KEY"]`로 접근, 하드코딩 금지
- 로그에 시크릿/토큰/비밀번호 출력 금지

```python
# GOOD
SECRET_KEY = os.environ["SECRET_KEY"]

# BAD — 절대 금지
SECRET_KEY = "sk-abc123..."
```

## SQL Injection 방지
- Raw SQL 사용 금지 — SQLAlchemy ORM 또는 `text()` 바인딩 사용
- f-string으로 SQL 쿼리 구성 절대 금지

```python
# GOOD — SQLAlchemy ORM
stmt = select(Company).where(Company.corp_code == corp_code)

# GOOD — 파라미터 바인딩
stmt = text("SELECT * FROM funds WHERE code = :code").bindparams(code=fund_code)

# BAD — SQL Injection 취약
stmt = text(f"SELECT * FROM funds WHERE code = '{fund_code}'")
```

## XSS 방지 (Frontend)
- `dangerouslySetInnerHTML` 사용 금지
- 사용자 입력을 직접 DOM에 삽입 금지

## JWT / 인증
- JWT secret은 최소 256-bit — 환경변수에서 로드
- 토큰 만료 시간 설정 필수 (`exp` claim)
- Refresh token rotation 적용
- 민감 API는 인증 미들웨어 필수 적용

## CORS 설정
- Production에서 `allow_origins=["*"]` 금지
- 허용 도메인을 환경변수로 관리

```python
# GOOD
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "").split(","),
    allow_credentials=True,
)

# BAD
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

## 파일 업로드 보안
- 파일 크기 제한 적용 (default: 50~100MB)
- 확장자 화이트리스트: `.xlsx`, `.xls`, `.csv`, `.pdf`, `.pptx`
- 파일명 sanitize — 경로 순회 공격 방지

## SSRF 방지 (크롤링)
- 외부 URL 요청 시 화이트리스트 도메인 검증
- Private IP 대역 (10.x, 172.16.x, 192.168.x) 접근 차단
- DART/KOFIA 등 공인 API만 허용

## Rate Limiting
- DART API: 100 req/min (900 req/min for premium)
- KOFIA API: 60 req/min
- 내부 API: slowapi 또는 커스텀 미들웨어

## Docker 보안
- 컨테이너에서 root 실행 금지 — `USER nonroot` 사용
- 빌드 시 시크릿 COPY 금지 — multi-stage build 사용
- `.dockerignore`에 `.env`, `.git`, `node_modules` 포함
- 베이스 이미지 태그 고정 (latest 금지)

## 의존성 보안
```bash
# Python (각 모듈별)
pip audit
# Node.js
cd amic-platform && npm audit
```
