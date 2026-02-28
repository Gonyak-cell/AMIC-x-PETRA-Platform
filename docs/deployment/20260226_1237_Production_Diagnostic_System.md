# 프로덕션 통합 진단 시스템 구축 보고서

> 작성: 2026-02-26 12:37
> 브랜치: feat/ma-workflow

## 배경

2026-02-26 프로덕션 배포 후 6개 에러가 5개 커밋에 걸쳐 순차적으로 수정됨.
한번에 전체 점검하는 시스템이 없어서 동일 카테고리를 여러 번 수정해야 했음.

### 2/26 에러 종합

| # | 모듈 | 에러 | 근본 원인 | 커밋 |
|---|------|------|----------|------|
| 1 | KIIS | 401 | JWT_SECRET 누락 | a331a6f |
| 2 | deal-mgmt | 500 | Alembic 체인 단절 + 중복 인덱스 | a331a6f, 7fca584 |
| 3 | IM | 401 | JWT_SECRET 누락 (KIIS와 동일 카테고리) | 4ef1860 |
| 4 | KIIS | CORS 실패 | 환경변수명 불일치 | 4ef1860 |
| 5 | nginx | CSP 차단 | script-src inline 미허용 | 4ef1860 |
| 6 | FDD/KIIS/MA | 500 | DB 볼륨 비밀번호 불일치 | bb03717 |

## 구현 산출물

### 1. `scripts/diagnose-production.sh` (신규)

10개 카테고리 통합 진단 스크립트:

| # | 카테고리 | 점검 내용 |
|---|---------|----------|
| 1 | 컨테이너 상태 | 16개 서비스 running 여부 |
| 2 | DB 연결 & 비밀번호 | 4개 DB SELECT 1 |
| 3 | DB 마이그레이션 | 4개 모듈 alembic current vs heads |
| 4 | JWT 일관성 | 4개 API JWT_SECRET 동일 여부 |
| 5 | CORS 설정 | 4개 API 환경변수명 + 형식 검증 |
| 6 | 헬스체크 | 4개 API /health 응답 + migration_ok |
| 7 | 크로스 모듈 인증 | FDD JWT → MA/KIIS 인증 테스트 |
| 8 | nginx & SSL | upstream, CSP, HSTS, 인증서 만료 |
| 9 | Redis/ES | KIIS Redis/ES, IM Redis/Celery |
| 10 | 디스크 & 리소스 | 메모리, 디스크, Docker 볼륨 |

사용법:
```bash
ssh -i "ssh/amic-platform-prod_key.pem" -o StrictHostKeyChecking=no azureuser@52.231.69.38 "cd /opt/amic-platform && bash scripts/diagnose-production.sh"
```

### 2. `.claude/rules/production-error-diagnostic.md` (신규)

프로덕션 에러 보고 시 자동 적용되는 Claude 규칙:
- 에러 수정 전 반드시 진단 스크립트 실행
- 단일 모듈 수정 금지 — 동일 카테고리 전체 모듈 점검 필수
- 에러 카테고리별 전수 점검 매트릭스 포함

### 3. `.github/workflows/deploy.yml` (수정)

| 변경 | 이전 | 이후 |
|------|------|------|
| 마이그레이션 실패 | `echo "WARN"` 후 계속 | 즉시 롤백 + exit 1 |
| 헬스체크 | HTTP 200만 확인 | 응답 본문(status, migration_ok) 검증 |
| 배포 후 | 없음 | diagnose-production.sh --ci 자동 실행 |

### 4. `docs/deployment/20260226_1231_ERROR_CATALOG.md` (신규)

15개 카테고리 프로덕션 에러 카탈로그:
- 증상, 근본 원인, 점검 대상, 수정 방법, 사례 포함
- 카테고리: 401, 403, 404, 422, DB(500), 마이그레이션(500), 502, 503, CORS, CSP, 로그인, 컨테이너, Redis/ES, SSL, 디스크

## UI 변경

### 버튼 색상 통일 (연두색)

| 파일 | 변경 내용 |
|------|----------|
| `Button.tsx` | primary variant: `bg-amic` → `bg-accent` (전체 30+ 버튼 일괄 적용) |
| `EmptyState.tsx` | CTA 버튼: `variant="primary"` → `variant="accent"` |

## 수정 파일 목록

| 파일 | 작업 |
|------|------|
| `scripts/diagnose-production.sh` | 신규 |
| `.claude/rules/production-error-diagnostic.md` | 신규 |
| `docs/deployment/20260226_1231_ERROR_CATALOG.md` | 신규 |
| `docs/deployment/20260226_1237_Production_Diagnostic_System.md` | 신규 |
| `.github/workflows/deploy.yml` | 수정 |
| `amic-platform/src/components/ui/Button.tsx` | 수정 |
| `amic-platform/src/components/ui/EmptyState.tsx` | 수정 |
