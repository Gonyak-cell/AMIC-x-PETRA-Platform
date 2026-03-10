---
name: continuous-review
description: 자동 순환 코드 리뷰. /loop 30m으로 호출하여 6라운드 13개 관점을 순환하며 경량 리뷰 수행. 허위 양성 최소화를 위해 VCP Lite 프로토콜 적용.
user-invokable: true
argument-hint: "[--round R1-R6] [--scope diff|module|files]"
---

# Continuous Review — 자동 순환 코드 리뷰

13개 리뷰 관점을 6라운드로 나누어 매 실행마다 1개 라운드씩 순환 리뷰합니다.
`/loop 30m /continuous-review` 또는 `/continuous-review` 직접 호출로 사용합니다.

**매 실행마다 fresh하게 코드를 읽습니다. 이전 리뷰 결과에 의존하지 않습니다.**

---

## 실행 흐름

```
Step 1: 상태 파일 읽기 → 이번 라운드 결정
Step 2: git diff로 변경 범위 결정
Step 3: 해당 라운드의 체크리스트로 리뷰 실행 (VCP Lite 적용)
Step 4: 리포트 저장 + 상태 파일 업데이트 + 사용자에게 요약 출력
```

---

## Step 1: 상태 파일 읽기 + 라운드 결정

### 상태 파일 읽기

Bash로 상태 파일을 확인합니다:

```bash
cat .claude/review-state.json 2>/dev/null || echo '{"current_round":1,"last_run":null,"history":[]}'
```

파일이 없으면 R1부터 시작합니다.

### 인자 처리

- `--round R3` 인자가 있으면 해당 라운드를 강제 실행 (상태 파일 무시)
- 인자 없으면 상태 파일의 `current_round` 사용

### 라운드 매핑

| 라운드 | 이름 | 관점 |
|--------|------|------|
| R1 | 기본 체크리스트 | 정합성 + 완전성 + 품질 + 안정성 |
| R2 | 보안 심층 | 보안 + STRIDE 위협 모델링 |
| R3 | 데이터 정합성 | 데이터 흐름 + API 계약 + BE-FE 타입 |
| R4 | 프로덕션 복원력 | 에러 처리 + 관찰 가능성 + 타임아웃 |
| R5 | 운영 & 코드 건강성 | 성능 + 배포 안전성 + 의존성 결합도 |
| R6 | 비즈니스 & UX | 도메인 로직 + 테스트 품질 + 가독성 + 접근성 |

---

## Step 2: 변경 범위 결정

### 기본: git diff (변경분만)

```bash
git diff --name-only master...HEAD
git diff --stat master...HEAD
```

- 변경 파일이 **0개**이면 → "변경 없음. 리뷰 건너뜀." 출력 후 종료 (상태 파일 변경 없음)
- 변경 파일이 **20개 초과**이면 → 변경량 상위 20개 파일만 대상으로 제한 (나머지는 다음 라운드에서 처리)

### 인자로 범위 지정

- `--scope diff` (기본값): `git diff master...HEAD`
- `--scope module ma`: 특정 모듈 디렉토리 전체 (`amic-platform/src/modules/ma/`)
- `--scope files path1 path2`: 특정 파일만

---

## Step 3: 라운드별 리뷰 실행

**이 단계가 핵심입니다.** 아래 라운드별 체크리스트에 따라 변경된 파일을 **직접 Read**로 읽고 리뷰합니다.

### !! 필수: VCP Lite 프로토콜 !!

**모든 이슈 보고 전에 반드시 적용합니다. 이 프로토콜을 건너뛰면 안 됩니다.**

#### 1단계 — Read 확인
- 이슈를 보고하기 전에 반드시 해당 파일을 **Read 도구로 직접 읽기**
- 메모리나 추론에 의존하지 않고 실제 코드를 확인
- 라인 번호가 정확한지 대조

#### 2단계 — Grep 검증
- "X가 없다" → **Grep으로 전체 코드베이스 검색**하여 부재 확인
- "X가 잘못 사용됨" → 주변 컨텍스트(import, 호출부, 설정 파일) 확인
- "X여야 한다" → 동일 모듈의 유사 코드와 비교 확인

#### 3단계 — Self-Challenge (SC-1/3/5)

이슈 초안 완성 후, **적대적 재검토자** 역할로 자기 반론:

| 항목 | 질문 | 판정 |
|------|------|------|
| **SC-1** 실행 경로 | 이 코드가 실제로 도달 가능한 경로인가? dead code, disabled 상태, feature flag? | ✓ 실행 가능 / ✗ REJECT / △ 조건부 |
| **SC-3** 라이브러리 동작 | React, Tanstack Query, FastAPI 등이 내부적으로 처리하는 기능을 "누락"으로 오판하지 않았는가? | ✓ 실제 이슈 / ✗ REJECT / △ 불확실 |
| **SC-5** 의도된 패턴 | 코드베이스 전체에서 동일 패턴이 사용되는가? Grep으로 확인. 일관된 패턴은 이슈가 아닐 수 있다. | ✓ 패턴 불일치 / ✗ REJECT / △ 불명확 |

**판정 결과**:
- SC-1~SC-5 중 **1개라도 ✗** → 해당 이슈 **기각** (보고하지 않음)
- **1개 이상 △** → 신뢰도 **MEDIUM** 이하로 하향
- **2개 이상 △** → 신뢰도 **LOW**로 하향

#### 절대 금지

- 추측성 표현: "아마", "~인 것 같다", "probably", "seems like"
- 메모리 기반 코드 인용: Read 없이 코드 언급
- 부재 미검증: "X가 없다"를 Grep 없이 주장
- 신뢰도 LOW 미만: 증거 불충분한 이슈는 보고하지 않음

---

### R1 — 기본 체크리스트

**정합성 검사**:
- [ ] 네이밍 컨벤션: BE snake_case, FE PascalCase(컴포넌트)/camelCase(함수) 일관성
- [ ] import 순서: stdlib → third-party → local
- [ ] 동일 모듈의 유사 파일을 Read로 1-2개 읽어 패턴 비교
- [ ] SQLAlchemy: `JSON().with_variant(JSONB, "postgresql")` + `Uuid` 사용 (JSONB/UUID 직접 금지)
- [ ] Pydantic v2: `model_config = ConfigDict(from_attributes=True)`, Create/Update/Response 분리

**완전성 검사**:
- [ ] 새 라우터 → `main.py`에 `include_router()` 등록 확인
- [ ] 새 페이지 → 라우팅 등록 + 사이드바/내비게이션 메뉴 추가 확인
- [ ] 에러 경로: 정상 경로만 구현하고 에러/예외 경로 누락 없는지
- [ ] 엣지 케이스: 빈 목록, null, 권한 없는 사용자, 존재하지 않는 리소스

**품질 검사**:
- [ ] 함수 길이 50줄 초과 여부
- [ ] 중복 코드 여부 (Grep으로 유사 패턴 검색)
- [ ] Python 타입 힌트 완비, TypeScript 제네릭/유니온 적절 활용
- [ ] 불필요한 상태 사용 (파생 가능한 값을 별도 state로 관리하지 않는지)

**안정성 검사**:
- [ ] 하드코딩된 시크릿/API 키/비밀번호 없는지
- [ ] 인증: 보호 엔드포인트에 `Depends(get_current_user)` 존재
- [ ] 입력 검증: Pydantic 또는 명시적 검증
- [ ] SQL 인젝션: 파라미터화된 쿼리 사용

---

### R2 — 보안 심층

**인증/인가 전수 검사**:
- [ ] 변경된 API 엔드포인트에 인증 데코레이터 유무 → Grep 전수 검사
- [ ] 쓰기 엔드포인트(POST/PUT/PATCH/DELETE)에 권한 체크
- [ ] JWT Secret: FDD=`jwt_secret`, KIIS/MA=`JWT_SECRET`, IM=`jwt_secret_key` — 하드코딩 없음

**입력 검증 & 인젝션**:
- [ ] SQL 쿼리 문자열 결합 패턴 Grep 검색: `f"SELECT`, `f"INSERT`, `f"UPDATE`, `+ "WHERE`
- [ ] 직접 HTML 삽입 사용 시 sanitize 여부
- [ ] CORS: 와일드카드(`*`) 미사용 확인

**STRIDE 위협 모델링**:
- [ ] **S**poofing: 인증 우회 경로 존재?
- [ ] **T**ampering: 서버 측 검증 누락? 클라이언트만 검증?
- [ ] **R**epudiation: 감사 로그(audit log) 존재?
- [ ] **I**nfo Disclosure: 에러 메시지에 내부 정보(스택 트레이스, DB 스키마) 노출?
- [ ] **D**oS: 대량 요청/대용량 업로드 제한?
- [ ] **E**levation of Privilege: 일반 사용자가 관리자 기능 접근 가능?

---

### R3 — 데이터 정합성

**데이터 흐름 추적**:
- [ ] 입력 → 가공 → 저장 → 반환 전체 경로를 코드에서 추적
- [ ] Race condition: 동시 업데이트, 중복 생성 가능성
- [ ] DB 트랜잭션 경계: 예외 발생 시 롤백 보장

**BE-FE 타입 계약**:
- [ ] BE Pydantic 스키마와 FE TypeScript 타입의 필드명/타입/nullable 일치 (양쪽 Read 비교)
- [ ] Enum 값 동기화: BE Enum과 FE 상수/타입 리터럴 일치
- [ ] API 경로/메서드: FE 호출 URL이 BE 라우터 경로와 정확히 매칭
- [ ] Breaking change 분류: 필드 추가=안전, 제거/이름변경=위험

**직렬화 검증**:
- [ ] Decimal/UUID/Enum → JSONB 저장 시 `_sanitize_for_json()` 거치기
- [ ] `json.dumps()` 후 JSONB 컬럼 할당 금지 (이중 직렬화)
- [ ] 금액 단위: 억=10^8, 조=10^12, 백만=10^6

---

### R4 — 프로덕션 복원력

**에러 처리**:
- [ ] try/except 범위: 너무 넓거나 좁지 않은지
- [ ] `except Exception:` 포괄 캐치 → 구체적 예외 타입 사용 권장
- [ ] DB 트랜잭션 롤백 보장
- [ ] 외부 서비스 장애 대응: 폴백/적절한 에러 반환

**타임아웃 & 재시도**:
- [ ] 외부 HTTP 호출에 타임아웃 설정
- [ ] DB 쿼리 타임아웃
- [ ] 무한 대기 가능 코드 경로

**관찰 가능성**:
- [ ] 구조화된 로깅 (JSON, contextual fields)
- [ ] 에러 로그에 충분한 컨텍스트 (요청 ID, 사용자 ID, 입력 값)
- [ ] 민감 데이터 로깅 금지 (비밀번호/토큰)
- [ ] 헬스체크에 DB ping 포함 여부

---

### R5 — 운영 & 코드 건강성

**성능**:
- [ ] N+1 쿼리 패턴: 루프 내 DB 호출
- [ ] `useMemo`/`useCallback` 필요한 곳에 누락
- [ ] 대용량 데이터 페이지네이션 누락
- [ ] 불필요한 전체 로딩 (SELECT * 패턴)

**배포 안전성**:
- [ ] DB 마이그레이션: `downgrade()` 실제 구현 (빈 함수/pass 금지)
- [ ] 환경변수 동기화: 새 환경변수 → config.py + .env.example + Docker compose
- [ ] 새 import → pyproject.toml dependencies 등록 확인
- [ ] deploy.yml `permissions:` 블록 보존 확인

**의존성 & 결합도**:
- [ ] 순환 의존성: A→B→C→A 패턴
- [ ] God Object: 한 클래스/모듈의 과도한 책임
- [ ] 변경 파급 효과: 이 수정이 다른 몇 개 파일에 영향?

---

### R6 — 비즈니스 & UX

**도메인 로직**:
- [ ] 비즈니스 규칙이 정확히 구현되었는지 (요구사항 대조)
- [ ] 적절한 계층 배치: 라우터에 비즈니스 로직 혼입 여부
- [ ] 계산 정확성: 경계값, 반올림, 통화 단위
- [ ] 도메인 용어 일관성 (Ubiquitous Language)

**테스트 품질**:
- [ ] 행동(behavior) 검증 vs 구현 세부 검증
- [ ] 경계값/실패 경로 테스트 존재
- [ ] Mock 과용 여부
- [ ] `pytest.raises(Exception)` 사용 시 `match=` 추가 (B017)

**가독성 & 복잡도**:
- [ ] 인지 복잡도: 중첩 조건문 3단 이상
- [ ] Magic number/string 사용
- [ ] Guard clause/Early return 활용
- [ ] 함수/변수 네이밍 명확성

**접근성 (FE 변경 시)**:
- [ ] 키보드 탐색 가능
- [ ] ARIA 속성 적절성
- [ ] 색상 대비 4.5:1
- [ ] 로딩/에러/빈 상태 처리

---

## 우선순위 계산

각 이슈에 우선순위 점수를 계산합니다:

```
점수 = 심각도 x 신뢰도

심각도: Critical(100) / Major(70) / Moderate(40) / Minor(20)
신뢰도: HIGH(1.0) / MEDIUM(0.6) / LOW(0.3)

P0 (90+):  즉시 수정 — 보안/데이터 무결성
P1 (60-89): 스프린트 우선 — 안정성/정확성
P2 (30-59): 개선 권장 — 코드 품질
P3 (<30):  저우선 — 개선 가능

예시:
- Critical + HIGH = 100 x 1.0 = 100 -> P0
- Critical + MEDIUM = 100 x 0.6 = 60 -> P1 (P0 아님!)
- Major + HIGH = 70 x 1.0 = 70 -> P1
- Moderate + LOW = 40 x 0.3 = 12 -> P3
```

---

## Step 4: 리포트 저장 + 상태 업데이트

### 리포트 저장

1. PowerShell로 현재 시간 확인:
```bash
powershell -Command "Get-Date -Format 'yyyyMMdd_HHmm'"
```

2. 리포트 파일 저장:
```bash
mkdir -p review/continuous
# 파일: review/continuous/YYYYMMDD_HHMM_R{N}_Review.md
```

### 상태 파일 업데이트

Bash로 `.claude/review-state.json`을 업데이트합니다:

```bash
# current_round를 다음 라운드로 (R6이면 R1으로)
# last_run을 현재 시간으로
# history에 이번 결과 추가 (최대 30건 유지)
```

```json
{
  "current_round": 다음_라운드_번호,
  "last_run": "YYYY-MM-DDTHH:MM:SS+09:00",
  "history": [
    {
      "round": 현재_라운드,
      "round_name": "라운드명",
      "timestamp": "...",
      "issues_found": N,
      "issues_by_priority": {"P0": 0, "P1": 1, "P2": 2, "P3": 0},
      "files_reviewed": N,
      "hypotheses_tested": N,
      "hypotheses_rejected": N
    }
  ]
}
```

---

## 리포트 형식

```markdown
# Continuous Review — R{N} ({라운드명})

> **Date**: YYYY-MM-DD HH:MM (KST)
> **Round**: R{N}/6
> **Scope**: git diff master...HEAD ({N}개 파일)
> **Protocol**: VCP Lite (Read->Grep->Self-Challenge SC-1/3/5)

## 변경 파일 요약

{git diff --stat master...HEAD 결과}

## 발견 이슈

### [{SEVERITY_INITIAL}-CR{NUMBER}] {제목} — [{심각도}/{신뢰도}] — Priority: {P0/P1/P2/P3}

- **파일**: `{경로}:{라인}`
- **카테고리**: R{N} {라운드명}
- **검증**: Read(V/X) Grep(V/X/N/A) SC-1(V/X/T) SC-3(V/X/T) SC-5(V/X/T)
- **증거**:
  {Read 도구에서 가져온 실제 코드 — 메모리 재구성 금지}
- **이슈**: {구체적 설명}
- **영향**: {문제 발생 시 어떤 일이 일어나는지}
- **수정안**:
  {제안하는 코드 변경}

{이슈가 없으면}:
> 이번 라운드에서 발견된 이슈가 없습니다.

## 검증 투명성

- 검증한 가설: N건
- 거부된 가설 (사전 제거): N건
- 보고된 이슈: N건
- 거부율: {거부 / (거부+보고)}%

### 거부 사유 분류 (1건 이상일 때)

| 사유 | 건수 |
|------|------|
| SC-1 실행 경로 기각 | N |
| SC-3 라이브러리 오해 기각 | N |
| SC-5 의도된 패턴 기각 | N |
| Grep 반증 | N |

## 다음 라운드

- 다음 실행: R{N+1} ({다음 라운드명})
```

---

## 사용자 요약 출력

리포트 저장 후, 사용자에게 간결한 요약을 출력합니다:

```
## Continuous Review 완료 — R{N} {라운드명}

- 대상: {N}개 변경 파일
- 이슈: {N}건 (P0:{n} P1:{n} P2:{n} P3:{n})
- 검증: 가설 {N}건 중 {N}건 거부 (거부율 {X}%)
- 리포트: review/continuous/YYYYMMDD_HHMM_R{N}_Review.md
- 다음: R{N+1} {다음 라운드명}
```

---

## 사용 예시

```bash
# 30분 주기 자동 리뷰
/loop 30m /continuous-review

# 수동 호출 (다음 라운드 자동 결정)
/continuous-review

# 특정 라운드 강제 실행
/continuous-review --round R2

# 특정 모듈만 리뷰
/continuous-review --scope module ma
```
