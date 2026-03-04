# 코드 리뷰 리포트: 인프라 — Chunk 1

- 라운드: 1
- 모듈: Chunk 1 인프라 & DevOps
- 배치: 전체 (읽기 전용 — infra-freeze 적용)
- 시작: 2026-03-05 03:33
- 종료: 2026-03-05 03:39

## infra-freeze 적용

Tier 1 파일(docker-compose image 태그, deploy.yml 게이트)은 리뷰/수정 모두 제외.
Tier 2 파일(nginx, entrypoint)은 관찰만 기록.
**이 청크에서 코드 수정은 0건.**

## Tier 1 — 완전 패스

- docker-compose.yml — 패스
- docker-compose.prod.yml — 패스
- docker-compose.ssl.yml — 패스
- .github/workflows/deploy.yml — 패스

## 관찰 사항 (수정 금지)

### Medium

| # | 관점 | 파일 | 관찰 | 조치 |
|---|------|-----|------|------|
| 1 | 보안 | .github/workflows/ci.yml | IM 모듈 Docker 스캔 누락 (FDD, KIIS, Deal-Mgmt는 포함) | 관찰만 |
| 2 | 설정 | deal-mgmt/ | .dockerignore 파일 부재 — 불필요한 파일이 이미지에 포함될 수 있음 | 관찰만 |

### Low

| # | 관점 | 파일 | 관찰 |
|---|------|-----|------|
| 3 | 설정 | Dockerfile들 | 베이스 이미지 버전 차이: FDD/KIIS=3.10-slim, IM=3.10-slim, DealMgmt=3.10 (non-slim) |
| 4 | 설정 | Dockerfile들 | pip install 전략: FDD/KIIS=requirements.txt, DM/IM=pyproject.toml |
| 5 | 보안 | Dockerfile들 | 모두 non-root USER 사용 ✅ |
| 6 | 설정 | nginx/ | prod.conf: 보안 헤더 (X-Frame-Options, CSP 등) 설정됨 ✅ |
| 7 | 설정 | */scripts/docker-entrypoint.sh | FDD/KIIS/DM: `set -e` 포함, IM: entrypoint 없음 (CMD 직접 사용) |
| 8 | 아키텍처 | scripts/ | 배포/유틸 스크립트 15개 — 일관된 구조 ✅ |
| 9 | 설정 | .husky/pre-push | Guard 1~7 자동 검증 포함 ✅ |
| 10 | 설정 | lefthook.yml | ruff auto-fix 훅 포함 ✅ |

## 검증 결과

- 코드 수정 없음 → 별도 검증 불요

## 에러 카운트

| 관점 | 관찰 | 수정 |
|------|------|------|
| 보안 | 1건 (Medium) | 0 (infra-freeze) |
| 설정 | 1건 (Medium) + 6건 (Low) | 0 (infra-freeze) |
| 아키텍처 | 2건 (Low) | 0 |
| 합계 | 10건 관찰 | 0건 수정 |

## 충족 관점 체크리스트

- [x] 9. 린트/포맷 (Dockerfile/shell 기본 품질 확인)
- [x] 1. 보안 (non-root, 보안 헤더 확인)
- [x] 8. 환경변수/설정 (베이스 이미지, 빌드 전략 관찰)
- [x] 3. 아키텍처 (스크립트 일관성 확인)
