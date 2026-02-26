# Infrastructure File Protection (인프라 파일 보호)

> **핵심**: 아래 파일들은 배포 안정성을 위해 검증/고정된 설정이다.
> 사용자가 **명시적으로** 수정을 요청하지 않는 한, 절대 변경하지 않는다.

## 적용 시점

아래 보호 대상 파일을 수정하려 할 때 **자동 적용**.
기능 개발, 리팩토링, 버그 수정 등 어떤 작업이든 관계없이 적용된다.

## 보호 대상 파일

### Tier 1: 절대 수정 금지 (사용자 명시 요청 + 확인 필수)

| 파일 | 보호 항목 | 이유 |
|------|----------|------|
| `docker-compose.yml` | `image:` 태그 | BuildKit 이미지 스왑 방지 |
| `docker-compose.prod.yml` | `image:` 태그, `--workers` 수 | 프로덕션 안정성 |
| `docker-compose.ssl.yml` | 전체 | SSL/인증서 설정 |
| `.github/workflows/deploy.yml` | 환경변수 검증 게이트, 빌드 명령어, 헬스체크 로직 | 배포 안전장치 |

### Tier 2: 수정 시 반드시 사용자 확인 필요

| 파일 | 보호 항목 | 이유 |
|------|----------|------|
| `nginx/prod.conf` | upstream, location 블록 | 프로덕션 라우팅 |
| `nginx/prod-nossl.conf` | 동일 | HTTP 폴백 라우팅 |
| `*/scripts/docker-entrypoint.sh` | 전체 | 컨테이너 시작 로직 |
| `*/main.py` 중 `lifespan` 함수 | 마이그레이션 호출 유무 | Alembic 중복 실행 방지 |
| `*/main.py` 중 `health_check` 함수 | DB ping 로직, 응답 필드 | 헬스체크 정확성 |

## 절대 금지 사항

1. **`image:` 태그 제거/변경 금지** — BuildKit 이미지 스왑의 원천 차단
2. **entrypoint/lifespan에 `alembic` 호출 추가 금지** — deploy.yml에서만 관리
3. **`--no-cache` 재추가 금지** — image 태그로 해결됨, --no-cache는 빌드 시간만 증가
4. **환경변수 검증 게이트 제거/우회 금지** — 필수 변수 누락 시 배포 차단
5. **헬스체크에서 DB ping 제거 금지** — 이미지 스왑/DB 장애 감지 필수
6. **workers 수 임의 증가 금지** — Azure VM 리소스 한계 (2 vCPU, 16GB RAM)

## "하는 김에" 수정 절대 금지

다른 기능을 개발하면서 위 파일들을 "개선"하거나 "정리"하는 것을 금지한다:
- ❌ "docker-compose.yml 포맷 정리하면서 image 태그 수정"
- ❌ "entrypoint 개선하면서 alembic 추가"
- ❌ "deploy.yml 최적화하면서 검증 게이트 간소화"
- ❌ "헬스체크 리팩토링하면서 DB ping 제거"

## 수정이 필요한 경우

1. 사용자가 **명시적으로** 수정을 요청한다
2. 수정 이유를 **구체적으로** 설명한다
3. **영향 범위**를 명시한다 (어떤 서비스에 영향이 가는지)
4. 사용자 확인 후에만 수정한다

## 관련 문서

- `docs/deployment/20260226_1429_FDD_MA_502_Fix.md` — 이미지 스왑 버그 원인/수정
- `.claude/rules/post-deploy-verification.md` — 배포 후 검증 절차
- `.claude/rules/production-error-diagnostic.md` — 프로덕션 에러 진단
