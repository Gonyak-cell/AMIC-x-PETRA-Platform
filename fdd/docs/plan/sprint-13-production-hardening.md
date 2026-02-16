# Sprint 13: Production Hardening & 실행 검증

> 작성일: 2026년 02월 08일
> 상태: PLANNED

---

## 목표

로컬/스테이징 환경에서 실제 구동 검증 + 모니터링 스택 구축 + 성능 최적화 + Beta Pilot 준비

---

## Phase 1: 로컬 구동 검증

| 작업 | 설명 | 상태 |
|------|------|------|
| Docker Compose 구동 | `make up` → 4서비스 기동 확인 | PENDING |
| DB 마이그레이션 | `make migrate` → Alembic 4개 버전 적용 | PENDING |
| 브라우저 접속 확인 | http://localhost:5173 → 로그인/딜 목록 표시 | PENDING |
| 전체 워크플로 테스트 | Deal 생성 → 업로드 → 매핑 → QoE/NWC/Debt → 리포트 | PENDING |
| Node.js 설치 | 로컬 개발 환경에 Node.js 20+ 설치 (E2E/lint 실행용) | PENDING |
| E2E 스모크 테스트 | `cd e2e && npm test` → Playwright 39 시나리오 | PENDING |

---

## Phase 2: CI/CD 강화

| 작업 | 설명 | 상태 |
|------|------|------|
| GitHub 리포 설정 | branch protection (main: 1 approver + CI pass) | PENDING |
| PR 템플릿 | `.github/pull_request_template.md` 추가 | PENDING |
| CI 워크플로 검증 | `ci.yml` + `e2e.yml` → GitHub Actions 실행 확인 | PENDING |
| CODEOWNERS | `.github/CODEOWNERS` — auth/, engines/ 영역 설정 | PENDING |

---

## Phase 3: 모니터링 & 관측성

| 작업 | 설명 | 상태 |
|------|------|------|
| Prometheus | docker-compose에 prometheus 서비스 추가 | PENDING |
| Grafana | docker-compose에 grafana 서비스 추가 | PENDING |
| 대시보드 | API 지연시간, 에러율, 엔진 처리 시간, 잡 성공률 | PENDING |
| 로그 수집 | Loki 또는 파일 기반 JSON 로그 수집 | PENDING |
| 알림 설정 | 에러율 > 1%, 지연 > 5s 시 알림 | PENDING |

---

## Phase 4: 성능 벤치마크

| 작업 | 설명 | SLA 목표 |
|------|------|----------|
| GL 인제스트 | 100만 행 Excel → DB 저장 | < 5분 |
| QoE 계산 | QoE Bridge 생성 | < 30초 |
| PPT 렌더링 | Report IR → PPT 파일 생성 | < 2분 |
| Word 렌더링 | Report IR → DOCX 파일 생성 | < 1분 |
| API 응답 | 95th percentile 응답 시간 | < 500ms |
| DB 쿼리 | Slow query 프로파일링 + 인덱스 최적화 | - |
| FE 번들 | Vite 코드 스플리팅 + lazy loading | < 500KB initial |

---

## Phase 5: Beta Pilot 준비

| 작업 | 설명 | 상태 |
|------|------|------|
| 스테이징 배포 | `docker-compose.prod.yml` + `scripts/deploy.sh up` | PENDING |
| 시크릿 설정 | `.env.production` — JWT_SECRET, DB 비밀번호, CORS | PENDING |
| SSL/TLS | 리버스 프록시 HTTPS 설정 (Nginx + certbot) | PENDING |
| 파트너 선정 | 2~3곳 파일럿 파트너 선정 | PENDING |
| 온보딩 실행 | `docs/operations/partner-onboarding.md` 체크리스트 | PENDING |
| 피드백 수집 | 사용자 피드백 폼 + 이슈 트래커 연동 | PENDING |

---

## 산출물

| 산출물 | 위치 |
|--------|------|
| Prometheus + Grafana 설정 | `docker-compose.monitoring.yml` |
| Grafana 대시보드 | `config/grafana/dashboards/` |
| PR 템플릿 | `.github/pull_request_template.md` |
| 성능 벤치마크 결과 | `docs/benchmarks/` |
| 스테이징 배포 완료 | 스테이징 서버 |

---

## 리스크

| 리스크 | 영향 | 완화 전략 |
|--------|------|-----------|
| Docker Desktop 미설치 | Phase 1 차단 | WSL2 + Docker Desktop 설치 가이드 |
| Node.js 미설치 | E2E/lint 불가 | Node.js 20 LTS 로컬 설치 |
| 스테이징 서버 부재 | Phase 5 지연 | 로컬 prod 모드로 대체 검증 |
| 성능 SLA 미달 | 파일럿 품질 | DB 인덱스 + 쿼리 최적화 |

---

## 의존성

- Docker Desktop 설치 및 실행
- Node.js 20+ 로컬 설치
- GitHub 리포지토리 push 권한
- 스테이징 서버 (클라우드 또는 온프레미스)
