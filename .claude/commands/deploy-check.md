---
name: deploy-check
description: 모노레포 전체 배포 전 검증 체크리스트를 실행합니다.
---
# 모노레포 배포 전 검증 체크리스트

## 1단계: 코드 품질

### Backend (각 모듈별)
- [ ] FDD 테스트 통과 (`cd fdd/backend && python -m pytest tests/ -v`)
- [ ] KIIS 테스트 통과 (`cd kiis && uv run pytest tests/ -v`)
- [ ] IM 테스트 통과 (`cd im && python -m pytest tests/ -v`)
- [ ] ruff check 경고 없음 (각 모듈)

### Frontend
- [ ] TypeScript 타입 체크 통과 (`cd amic-platform && npx tsc --noEmit`)
- [ ] ESLint 경고 없음 (`cd amic-platform && npx eslint src/`)
- [ ] Vite 빌드 성공 (`cd amic-platform && npm run build`)

## 2단계: DB 마이그레이션
- [ ] FDD: `cd fdd/backend && alembic current` — 최신 버전 확인
- [ ] KIIS: `cd kiis && uv run alembic current` — 최신 버전 확인
- [ ] IM: `cd im && alembic current` — 최신 버전 확인
- [ ] 파괴적 마이그레이션 없음 (또는 롤백 계획 수립)

## 3단계: Docker 빌드
- [ ] `docker compose build` 성공
- [ ] 모든 컨테이너 healthy (`docker compose ps`)
- [ ] Nginx 설정 문법 검사

## 4단계: 환경 설정
- [ ] `.env.production.example` 최신화 (새 환경변수 추가 시)
- [ ] CORS_ORIGINS 환경변수 설정 확인 (기본값 없어야 함)
- [ ] 환경별 설정 분리 확인 (dev/staging/prod)

## 5단계: 보안
- [ ] 하드코딩된 시크릿 없음
- [ ] @backend-security-reviewer 에이전트로 보안 검토
- [ ] 의존성 취약점 해결:
  - `pip audit` (각 백엔드)
  - `cd amic-platform && npm audit`
- [ ] CORS/인증 설정 프로덕션 모드 확인

## 6단계: 최종 판정
모든 항목 통과 시 "DEPLOY READY" 출력.
실패 항목이 있으면 상세 사유와 해결 방법을 제시하세요.
