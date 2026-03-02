# Top 8 에러 사전 차단 규칙 (938건 에러 로그 + 70건 수정 커밋 기반)

> **핵심**: 실제 에러 데이터에서 도출된 8대 반복 에러 패턴을 사전 차단한다.
> 상세 코드 예시와 Review Gate는 `/error-prevention-detail` 스킬 참조.

## 적용 시점

**모든 코드 작성/수정/리뷰 시 자동 적용.**

---

## 빠른 참조: Pre-flight 체크 요약

| # | 위험 | 확인 질문 | 실패 시 영향 | 빈도 |
|---|------|---------|-----------|------|
| **P1** | 타입 불일치 | Badge/Button variant 유효? BE Enum = FE? | tsc 실패, 렌더링 오류 | 15건 fix |
| **P2** | 직렬화 실패 | `_json_safe` 거쳤는가? `json.dumps` 이중 직렬화 없는가? | PATCH 500 | 12건 fix |
| **P3** | 환경변수 불일치 | 모듈별 config.py 패턴과 일치하는가? | 401, CORS 차단 | 10건 fix |
| **P4** | 마이그레이션 누락 | 모델 변경에 대응하는 마이그레이션 존재? downgrade() 구현? | 배포 시 500 | 5건 fix |
| **P5** | 보안 누락 | 인증 Depends 주입? JWT 하드코딩 없음? | 미인증 접근 | 8건 fix |
| **P6** | Ruff 린트 | `ruff check` 0건? `pytest.raises(match=)` 사용? | CI 실패 | **127건/3일** |
| **P7** | 의존성 누락 | 새 import가 pyproject.toml에 등록? | Docker 빌드 실패 | 다수 |
| **P8** | 인코딩/경로 | UTF-8 명시? pathlib 사용? 한글 경로 따옴표? | UnicodeError | **84건/3일** |
| **P9** | pytest 환경 불일치 | addopts에 플러그인 옵션 사용 시 dev 의존성 등록? | pytest 실행 실패 | 3건 |

---

## P1: TypeScript/Python 타입 불일치

### Pre-flight 체크
- [ ] UI 컴포넌트 variant가 유효 값인지 확인 (Badge: success/warning/error/info/neutral, Button: primary/secondary/ghost/danger/accent/brand)
- [ ] Pydantic Enum 변경 시 FE TypeScript 리터럴과 양쪽 `Read`로 대조
- [ ] Python 타입 힌트: `str | None` 사용 (`Optional[str]` 금지)

## P2: 데이터 직렬화/타입 변환 실패

### Pre-flight 체크
- [ ] Decimal/UUID/Enum → JSONB 저장 시 `_sanitize_for_json()` 거치기 (`audit_service.py:37`)
- [ ] `json.dumps()` 후 JSONB 컬럼에 할당하지 않기 (이중 직렬화)
- [ ] 금액 단위: 억=10^8, 조=10^12, 백만=10^6
- [ ] 크로스 DB: `Uuid` + `JSON().with_variant(JSONB, "postgresql")` 사용

## P3: 환경변수/설정 불일치

### Pre-flight 체크
- [ ] CORS: FDD=`str`(쉼표), KIIS/IM/MA=`list[str]`(JSON 배열) — 형식 혼용 금지
- [ ] JWT: FDD=`jwt_secret`(소문자), KIIS/MA=`JWT_SECRET`(대문자), IM=`jwt_secret_key`(alias `JWT_SECRET`)
- [ ] 새 환경변수 → config.py + `.env.example` + Docker compose 동기화
- [ ] 4개 모듈 공통 설정(JWT_SECRET)은 동일 값 확인

## P4: 마이그레이션/스키마 누락

### Pre-flight 체크
- [ ] 모델 변경 → 대응 Alembic 마이그레이션 존재?
- [ ] `down_revision` 체인 정확? (`alembic heads` = 1개)
- [ ] `downgrade()` 실제 롤백 SQL 포함? (빈 함수/pass 금지)
- [ ] `models/__init__.py`에 새 모델 import 추가?

## P5: 보안/권한 데코레이터 누락

### Pre-flight 체크
- [ ] 새 엔드포인트에 인증 Depends 주입? (FDD: `get_current_user`, KIIS: `get_current_active_user`, IM: `get_current_user`, MA: `get_jwt_claims`)
- [ ] 쓰기 엔드포인트에 권한 체크?
- [ ] JWT_SECRET 하드코딩 없음? (빈 문자열 기본값만 허용)

## P6: Ruff 린트 위반

### Pre-flight 체크
- [ ] Python 파일 수정 후 `ruff check . && ruff format --check .` 실행 (0건 필수)
- [ ] `pytest.raises(Exception)` / `pytest.raises(BaseException)` 사용 시 반드시 `match=` 추가 (B017)
  - 구체적 예외(ValueError, HTTPException 등)는 match= 없이도 허용
- [ ] import 작성 후 실제 사용 여부 확인 (F401)
- [ ] **`asyncio.TimeoutError` 사용 금지** → 빌트인 `TimeoutError` 직접 사용 (UP041)
- [ ] auto-format 훅에 의존 금지 — B017, N802 등은 자동 수정 불가, 처음부터 올바르게 작성

## P7: 의존성 누락

### Pre-flight 체크
- [ ] 새 `import` → 해당 모듈 `pyproject.toml`에 등록 확인
- [ ] dev 전용 → `[project.optional-dependencies] dev = [...]`에 추가

## P8: 인코딩/경로 에러

### Pre-flight 체크
- [ ] `open()` 호출 시 `encoding="utf-8"` 명시 (바이너리 모드 제외)
- [ ] 파일 경로: `pathlib.Path` 사용 (하드코딩 절대 경로 금지)
- [ ] Bash 명령어에서 한글/공백 경로 따옴표로 감싸기

## P9: pytest 플러그인/환경 의존성 불일치

### Pre-flight 체크
- [ ] `[tool.pytest.ini_options] addopts`에 `--cov` 등 플러그인 옵션 → `[project.optional-dependencies] dev`에 해당 패키지 등록 확인
- [ ] 로컬 pytest 실행 시 `--cov` 에러 발생 → `-o "addopts="` 로 오버라이드 가능
- [ ] 새 pytest 플러그인 추가 시 pyproject.toml dev 의존성 동기화

---

## 위반 감지 신호

다음을 쓰거나 생각하면 **STOP — 이 규칙으로 돌아가기**:

- "이 variant 이름은 맞을 것이다" → **P1 참조 테이블 확인**
- "dict를 그냥 JSONB에 넣으면 되겠지" → **P2 _json_safe 확인**
- "다른 모듈 환경변수 이름도 같겠지" → **P3 매핑 테이블 확인**
- "마이그레이션은 나중에 만들면 되지" → **P4 동반 체크리스트 확인**
- "이 엔드포인트는 public이니까 인증 없어도 되지" → **P5 보안 체크리스트 확인**
- "ruff는 나중에 돌리면 되지" → **P6 즉시 검증 필수**
- "이 패키지는 이미 설치되어 있겠지" → **P7 pyproject.toml 확인**
- "open()에 encoding 안 써도 되겠지" → **P8 UTF-8 명시 필수**
- "`asyncio.TimeoutError`를 써야지" → **P6 UP041: TimeoutError 사용**
- "pytest-cov 없어도 pytest는 돌아가겠지" → **P9 addopts 확인**

---

## 기존 규칙 참조

| 항목 | 상세 규칙 |
|------|----------|
| P2 크로스 DB 타입 | `ci-regression-prevention.md` Guard 2 |
| P3 CORS 형식 | `/prod-diagnostic` 스킬 |
| P6 Ruff 린트 | `python-ci-standards.md` 강행 규정 1 |
| P8 인코딩/경로 | `python-ci-standards.md` 강행 규정 2 |
| 상세 코드 예시 | `/error-prevention-detail` 스킬 |
