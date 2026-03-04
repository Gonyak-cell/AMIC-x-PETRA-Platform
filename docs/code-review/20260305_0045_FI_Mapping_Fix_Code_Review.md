# Code Review — FI 자동 매핑 수정 (d13f8a8)

> **Review Date**: 2026-03-05 00:45
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 커밋 d13f8a8 — 8 files (6 code + 2 xlsx)
> **Method**: Quality Gates + Verified Multi-Agent Review (3 agents)
> **Quality Gates**: tsc(PASS) eslint(PASS) ruff-check(PASS) ruff-format(PASS)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 1     | HIGH: 1 | P1: 1 |
| Moderate | 2     | HIGH: 1 / MEDIUM: 1 | P2: 1 / P3: 1 |
| Minor    | 5     | HIGH: 3 / MEDIUM: 1 / LOW: 1 | P3: 5 |
| **Total**| **8** | HIGH: **5** / MEDIUM: **2** / LOW: **1** | P1: **1** / P2: **1** / P3: **6** |

**FP Prevention**: Critical/Major 0건 기능 결함 — INFRA-01은 일관성 개선 사항 (기능 정상 동작 확인됨)

---

## Findings

### [INFRA-01] 시드 데이터 경로 불일치 — [Major/HIGH] — Priority: P1 (점수: 70)

- **위치**: `deal-mgmt/scripts/seed_gp_profiles.py:28` vs `seed_pef_registry.py:30`
- **설명**: PEF 시드는 `data/fss_pef_registry.xlsx`, GP 시드는 `app/marketing/MA_GP_v3.xlsx` 참조. 두 시드 스크립트의 데이터 경로 규칙이 불일치. 기능적으로 정상 동작하나 관리 일관성 부족.
- **증거**:
  ```python
  # seed_pef_registry.py:30
  DEFAULT_XLSX = Path(__file__).resolve().parent.parent / "data" / "fss_pef_registry.xlsx"
  # seed_gp_profiles.py:28
  EXCEL_PATH = Path(__file__).resolve().parent.parent / "app" / "marketing" / "MA_GP_v3.xlsx"
  ```
- **권장**: 향후 `MA_GP_v3.xlsx`를 `data/`로 이동하여 통합. 즉시 수정 불필요.

### [R1] 날짜 truncation `[:10]` edge case — [Moderate/HIGH] — Priority: P2 (점수: 40)

- **위치**: `deal-mgmt/scripts/seed_pef_registry.py:64`
- **설명**: `str(row[4]).strip()[:10]`은 datetime 객체에서는 정상 작동하나, 비표준 문자열 형식(`"2024.01.15"` 등)이 들어오면 YYYY-MM-DD 보장 불가. 현재 금감원 데이터는 안전하나, 데이터 소스 변경 시 잠재적 위험.
- **권장**: 날짜 정규화 함수(`datetime.strptime` + `strftime`) 도입 고려.

### [R3] engine.dispose() finally 패턴 미적용 — [Moderate/MEDIUM] — Priority: P3 (점수: 24)

- **위치**: `deal-mgmt/scripts/seed_pef_registry.py:81-125`
- **설명**: 예외 발생 시 `engine.dispose()`가 호출되지 않음. SQLAlchemy context manager가 자동 롤백하므로 데이터 유실은 없으나, 엔진 리소스 정리가 GC에 의존.
- **권장**: `try/finally`로 `engine.dispose()` 감싸기.

### [R5] 단위 변환 상수 인라인 — [Minor/HIGH] — Priority: P3 (점수: 20)

- **위치**: `deal-mgmt/app/routers/pef_registry.py:195`
- **설명**: `Decimal("100000000")`이 인라인 리터럴. 기능적으로 올바르나 의미 파악에 한 단계 필요.
- **참고**: ruff N806으로 인해 함수 내 대문자 상수 불가 — 모듈 상단 정의 필요.

### [R2] idempotent 임계값 100 매직넘버 — [Minor/HIGH] — Priority: P3 (점수: 20)

- **위치**: `deal-mgmt/scripts/seed_pef_registry.py:87`
- **설명**: `existing >= 100` 임계값이 명명되지 않은 상수. deploy.yml에서도 동일 값 사용.
- **권장**: `_MIN_SEEDED_THRESHOLD = 100` 상수 추출.

### [INFRA-02] Step 번호 체계 불일치 — [Minor/HIGH] — Priority: P3 (점수: 20)

- **위치**: `.github/workflows/deploy.yml:294, 310`
- **설명**: 기존 `[5.5/8]` ~ `[5.8/8]` 패턴 vs 신규 `[5.7.1]`, `[5.7.2]` — 총 개수 표시 미포함.
- **권장**: `[5.7.1/10]` 형식으로 통일 또는 서브스텝 체계 명시.

### [INFRA-03] .dockerignore 부재 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

- **위치**: `deal-mgmt/` 루트
- **설명**: `.dockerignore` 없어 `__pycache__`, `.env` 등이 빌드 컨텍스트에 포함될 수 있음. 현재 영향 미미.
- **권장**: `.dockerignore` 추가하여 불필요 파일 제외.

### [R4] 테이블 미존재 시 에러 처리 부재 — [Minor/LOW] — Priority: P3 (점수: 6)

- **위치**: `deal-mgmt/scripts/db_stats.py:47-49`
- **설명**: 마이그레이션 미실행 환경에서 ProgrammingError 발생 가능. deploy.yml에서 마이그레이션 후 호출되므로 현재 안전.

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)
1. [INFRA-01] [Major/HIGH]: 시드 데이터 경로 불일치 — seed scripts (점수: 70)

### P2 — 개선 권장 (점수: 30-59)
1. [R1] [Moderate/HIGH]: 날짜 truncation edge case — seed_pef_registry.py:64 (점수: 40)

### P3 — 저우선 (점수: <30)
1. [R3] [Moderate/MEDIUM ⚠️]: engine.dispose() finally — seed_pef_registry.py (점수: 24, 신뢰도 하향)
2. [R5] [Minor/HIGH]: 단위 변환 상수 인라인 — pef_registry.py:195 (점수: 20)
3. [R2] [Minor/HIGH]: 매직넘버 100 — seed_pef_registry.py:87 (점수: 20)
4. [INFRA-02] [Minor/HIGH]: Step 번호 체계 — deploy.yml (점수: 20)
5. [INFRA-03] [Minor/MEDIUM]: .dockerignore 부재 (점수: 12)
6. [R4] [Minor/LOW]: 테이블 미존재 에러 — db_stats.py (점수: 6)

---

## 잘된 점

- **단위 변환 정확성**: `Decimal("100000000")` 문자열 리터럴로 부동소수점 정밀도 유지
- **Parameterized SQL**: seed 스크립트에서 바인드 파라미터 사용 (SQL injection 방지)
- **infra-freeze 준수**: deploy.yml의 permissions, 환경변수 검증 게이트, 빌드 명령어, 헬스체크 미변경
- **Non-blocking 실패 처리**: PEF/GP seed 실패 시 WARN만 출력, 배포 미중단
- **FE 접근성 보존**: aria-live, role="list", tabIndex 등 기존 a11y 속성 유지
- **기존 패턴 일관성**: deploy.yml의 MIGRATE_MA 조건, SI_STATS JSON 파싱, timeout 패턴 준수

---

## Methodology

- **Agents**: code-reviewer (BE), code-reviewer (Infra), code-reviewer (FE)
- **Files scanned**: 6 code files + 2 xlsx data files
- **Protocol**: Verified Claim Protocol v1.1
- **Cross-verification**: INFRA-01 (Major) — 에이전트 자체 확인 "기능 정상 동작"
- **Phase 0A**: tsc(PASS) eslint(PASS) ruff-check(PASS) ruff-format(PASS)
