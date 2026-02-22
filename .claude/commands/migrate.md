---
name: migrate
description: 특정 백엔드 모듈의 Alembic 마이그레이션 워크플로우. 사용법 /migrate {module} {description}
---
# 데이터베이스 마이그레이션 워크플로우

모듈 및 설명: $ARGUMENTS
(예: `fdd add_status_column`, `kiis add_reputation_index`, `im add_data_source`)

## 0단계: 모듈 확인
인자에서 모듈명 파싱 (fdd / kiis / im):
- **fdd**: `cd fdd/backend && alembic ...`
- **kiis**: `cd kiis && uv run alembic ...`
- **im**: `cd im && alembic ...`

## 1단계: 현재 상태 확인
- `alembic current` — 현재 마이그레이션 버전 확인
- `alembic history` — 마이그레이션 이력 확인
- SQLAlchemy 모델 변경사항 파악 (git diff)

## 2단계: 마이그레이션 생성
- `alembic revision --autogenerate -m "{description}"` 실행
- 생성된 마이그레이션 파일 검토

## 3단계: 안전성 검토
- @migration-validator 에이전트로 마이그레이션 파일 검토
- 파괴적 작업(DROP, ALTER TYPE) 여부 확인
- upgrade/downgrade 대칭성 확인
- NUMERIC(18,4) monetary 컬럼 타입 확인

## 4단계: 테스트 실행
- 테스트 DB에서 `alembic upgrade head` 실행
- `alembic downgrade -1` 후 재 `upgrade`로 왕복 테스트
- 관련 단위 테스트 실행

## 5단계: 결과 보고
- 마이그레이션 요약 (추가/변경/삭제된 테이블/컬럼)
- 리뷰어 지적사항 및 조치 결과
- 프로덕션 적용 시 주의사항 (있는 경우)
