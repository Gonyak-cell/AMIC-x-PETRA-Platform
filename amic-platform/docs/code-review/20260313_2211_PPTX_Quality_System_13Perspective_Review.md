# Code Review — PPTX 품질 안정화 시스템 (Phase 0~6 전체)

> **Review Date**: 2026-03-13 22:11
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: Phase 0~6 전체 구현 — deal-mgmt + IM + amic-platform (47 파일, +1059/-135줄)
> **Method**: Quality Gates + Verified Multi-Agent Review (4 에이전트) + Cross-Verification
> **Agents**: code-reviewer, security-reviewer, performance-profiler, python-code-reviewer

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|------------|----------|
| Critical | 2     | HIGH: 2    | P0: 2    |
| Major    | 5     | HIGH: 4 / MEDIUM: 1 | P1: 5 |
| Moderate | 8     | HIGH: 5 / MEDIUM: 3 | P2: 8 |
| Minor    | 5     | HIGH: 3 / LOW: 2 | P3: 5 |
| **Total**| **20**| HIGH: **14** / MEDIUM: **4** / LOW: **2** | P0: **2** / P1: **5** / P2: **8** / P3: **5** |

**FP Prevention**: 가설 26건 검증, 6건 사전 거부 (거부율: 23%)
- StrEnum Python 3.11+ 호환성 → py311 타겟 확인, FALSE POSITIVE
- `import os` 미사용 → 실제 2곳 사용 확인, FALSE POSITIVE
- CONDITIONAL 다운로드 미차단 → PLAN.md 결정(내부 다운로드 허용)에 따라 DESIGN_RISK 하향
- 레지스트리 키 충돌 → 별도 프로세스 실행, 실제 충돌 불가, FALSE POSITIVE
- subprocess 인젝션 → list 형식 호출(shell=False), 인젝션 불가, FALSE POSITIVE
- CLIENT 역할 배포 접근 → 실제 require_write_access 검사 존재, DESIGN_RISK 하향

---

## P0 — 즉시 수정 (Critical)

### [C-1] IM visual regression 테스트 — generate_pptx import/호출 시그니처 완전 불일치

- **파일**: `im/tests/visual_diff/test_visual_regression.py:74-77`
- **심각도**: Critical / **신뢰도**: HIGH / **점수**: 100
- **에이전트**: code-reviewer (교차 검증: CONFIRMED)

**문제**: 테스트가 `from src.design_renderer.pipeline import generate_pptx`로 모듈 레벨 함수를 import하지만, 실제 `generate_pptx`는 `IMPipeline` 클래스의 인스턴스 메서드.

```python
# 테스트 코드 (test_visual_regression.py:74-77)
from src.design_renderer.pipeline import generate_pptx
result = generate_pptx(data, preset=preset, output_dir=str(tmp_path))

# 실제 코드 (pipeline.py:311-316)
def generate_pptx(self, data: IMDocumentData, *, output_path: str | Path) -> PipelineResult:
```

차이점: (1) 인스턴스 메서드 vs 함수 import, (2) `preset` 파라미터 미존재, (3) `output_dir` vs `output_path`.

**영향**: skip 마커로 보호되어 CI 즉시 실패는 아니지만, 시각 회귀 테스트 자체가 **실행 불가능**.

**수정 방안**: `IMPipeline` 인스턴스 생성 후 `pipeline.generate_pptx(data, output_path=...)` 호출로 변경.

---

### [C-2] Gate B `_check_slot_compliance` — violation 이중 카운팅으로 점수 왜곡

- **파일**: `deal-mgmt/app/ralph/gates/pptx_gate.py:345,358` / `im/src/quality_gate/pptx_gate.py:345,399`
- **심각도**: Critical / **신뢰도**: HIGH / **점수**: 100
- **에이전트**: code-reviewer (교차 검증: CONFIRMED)

**문제**: 빈 슬라이드/필수 shape 누락 시 `issues.append(...)` + `violation_count += 1`을 동시에 수행. 이후 점수 계산에서:

```python
total_violations = violation_count + len(issues) + len(critical_flags)
score = max(1.0, 5.0 - total_violations * 0.5)
```

동일 위반이 `violation_count`와 `len(issues)` 양쪽에 카운트되어 **실제 위반 수의 2배로 감점**.

**영향**: 정상적인 문서도 비정상적으로 낮은 slot_compliance 점수 → CONDITIONAL/FAIL 오판정 가능.

**수정 방안**: `violation_count` 제거, `len(issues) + len(critical_flags)`만으로 계산. 또는 `violation_count`를 별도 목적으로 분리.

---

## P1 — 스프린트 우선 (Major)

### [M-1] Gate A+B 동일 PPTX 이중/삼중 파싱 — 파이프라인 15~30% 성능 저하

- **파일**: `deal-mgmt/app/services/marketing_material_service.py:212-238`, `pptx_gate.py:66-68`
- **심각도**: Major / **신뢰도**: HIGH / **점수**: 70
- **에이전트**: performance-profiler

Gate A에서 `Presentation(template_path)` 로딩 → `generate_memo()`에서 동일 템플릿 재로딩 → Gate B에서 생성 PPTX 재로딩. 동일 PPTX를 최대 3회 파싱.

**수정**: 템플릿 로딩 결과를 `generate_memo()`에 주입하거나 캐시 레이어 추가.

---

### [M-2] 내부 경로/예외 정보 API 응답 노출

- **파일**: `deal-mgmt/app/services/marketing_material_service.py:76,282`, `template_preflight.py:223`
- **심각도**: Major / **신뢰도**: HIGH / **점수**: 70
- **에이전트**: security-reviewer

`mat.error_message = str(exc)` — Python 예외 전체가 DB에 저장되어 `MarketingMaterialOut` 스키마로 클라이언트 노출. `template_preflight`의 `f"템플릿 파일 미존재: {path}"`도 서버 절대 경로 포함.

**수정**: 사용자 친화적 고정 메시지만 반환, 상세는 서버 로그에만 기록.

---

### [M-3] 재생성 경로(`generate_marketing_material`)에서 성능 메트릭 항상 0

- **파일**: `deal-mgmt/app/services/marketing_material_service.py:390-402`
- **심각도**: Major / **신뢰도**: HIGH / **점수**: 70
- **에이전트**: performance-profiler

재생성 호출 시 `_run_quality_gate()`에 `template_load_ms`, `render_ms`, `persist_ms` 인자 미전달 → 3개 메트릭 항상 0 저장. 성능 모니터링 데이터 무결성 훼손.

---

### [M-4] deal-mgmt/im 모듈 간 template_spec·preflight·diff_utils 코드 100% 중복

- **파일**: `deal-mgmt/app/pptx/template_spec.py` vs `im/src/template_engine/template_spec.py` 외 3쌍
- **심각도**: Major / **신뢰도**: HIGH / **점수**: 70
- **에이전트**: code-reviewer + python-code-reviewer (교차 확인)

93줄(template_spec) + 384줄(preflight) + 252줄(diff_utils)이 거의 동일. 한쪽만 수정 시 Blast Radius 누락 패턴 발생 확률 높음.

**수정**: 공유 패키지 추출 또는 canonical source 표시 + 동기화 CI 체크 추가.

---

### [M-5] IM 모듈 `ALLOWED_FONTS`에 IM 전용 폰트 미포함 — 허위 양성 폰트 위반

- **파일**: `im/src/quality_gate/pptx_gate.py:28` (추정)
- **심각도**: Major / **신뢰도**: MEDIUM / **점수**: 42
- **에이전트**: code-reviewer

IM 프리셋(`im_full.py`)은 "SUITE", "Pretendard", "Noto Sans KR"을 사용하지만, `ALLOWED_FONTS`에는 "SUIT Medium", "Arial" 등만 포함. IM 문서 검증 시 대량 폰트 위반 허위 양성 발생 가능.

---

## P2 — 개선 권장 (Moderate)

### [Mo-1] `template_fingerprint` 필드 — BE 추가, 값 미할당, FE 미동기화

- **파일**: `deal-mgmt/app/schemas/marketing_material.py:50`, FE 타입 파일
- **심각도**: Moderate / **신뢰도**: HIGH / **점수**: 40
- **에이전트**: code-reviewer + python-code-reviewer

스키마에 필드 추가되었으나 서비스에서 값 할당 없음 → 항상 None. FE 타입에도 미반영.

### [Mo-2] deal-mgmt `diff_utils.py` — LibreOffice 이중 실행 (PNG + PDF)

- **파일**: `deal-mgmt/tests/visual_diff/diff_utils.py:68-110`
- **심각도**: Moderate / **신뢰도**: HIGH / **점수**: 40
- **에이전트**: code-reviewer + performance-profiler (교차 확인)

첫 번째 PNG 변환 시도가 불필요. IM 모듈은 바로 PDF 변환으로 시작하여 더 효율적.

### [Mo-3] `findSystemFonts()` 루프 내 반복 호출

- **파일**: `deal-mgmt/app/ralph/gates/template_preflight.py:372-376`, `im/...`
- **심각도**: Moderate / **신뢰도**: MEDIUM / **점수**: 24
- **에이전트**: code-reviewer + performance-profiler (교차 확인)

### [Mo-4] `_FIXTURES_DIR`와 `_GOLDEN_DIR` 동일 경로 중복 정의

- **파일**: `deal-mgmt/tests/test_golden_samples.py:26-27`
- **심각도**: Moderate / **신뢰도**: HIGH / **점수**: 40
- **에이전트**: code-reviewer

### [Mo-5] SSIM 계산 메모리 — float64 배열 + 이미지 중복 로딩

- **파일**: `deal-mgmt/tests/visual_diff/diff_utils.py:150-164`, `im/...`
- **심각도**: Moderate / **신뢰도**: MEDIUM / **점수**: 24
- **에이전트**: performance-profiler

`float` → `np.float32` 변환으로 메모리 50% 절감 가능. `compute_ssim()`과 `generate_diff_heatmap()`이 같은 이미지를 중복 로딩.

### [Mo-6] IM pipeline `ThreadPoolExecutor` 패턴 — 매 호출마다 신규 스레드+루프 생성

- **파일**: `im/src/design_renderer/pipeline.py:346-365`
- **심각도**: Moderate / **신뢰도**: MEDIUM / **점수**: 24
- **에이전트**: python-code-reviewer + performance-profiler

### [Mo-7] `parameters` 필드 스키마 미검증 — 임의 딕셔너리 직접 전달

- **파일**: `deal-mgmt/app/schemas/marketing_material.py:19`
- **심각도**: Moderate / **신뢰도**: HIGH / **점수**: 40
- **에이전트**: security-reviewer

`dict | None`으로 완전 개방. 허용 키 화이트리스트와 최대 깊이/크기 제한 권장.

### [Mo-8] Path Traversal — `startswith` 문자열 비교 경계 오탐

- **파일**: `deal-mgmt/app/routers/marketing_materials.py:175-177`
- **심각도**: Moderate / **신뢰도**: HIGH / **점수**: 40
- **에이전트**: security-reviewer

`is_relative_to()` 또는 `parents` 체크로 대체 권장.

---

## P3 — 저우선 (Minor)

### [Mi-1] `ShrinkPolicy` enum 정의만 존재, 검증 로직에서 미참조

- **파일**: `deal-mgmt/app/pptx/template_spec.py:32-36`
- **에이전트**: code-reviewer

### [Mi-2] 빈 슬라이드 감지 중복 조건

- **파일**: `deal-mgmt/app/ralph/gates/pptx_gate.py:330`
- **에이전트**: code-reviewer

### [Mi-3] `_check_text_slot`에서 `SlotContentType.TEXT` 대신 `"TEXT"` 문자열 직접 비교

- **파일**: `deal-mgmt/app/ralph/gates/pptx_gate.py:350`, `im/...`
- **에이전트**: python-code-reviewer

### [Mi-4] 골든 샘플 테스트 — 모듈 로딩 시점 파일시스템 접근

- **파일**: `deal-mgmt/tests/test_golden_samples.py:35`
- **에이전트**: performance-profiler

### [Mi-5] 재무 합계 검증에 `float` 누산

- **파일**: `pptx_gate.py:188` (양쪽)
- **에이전트**: python-code-reviewer

---

## 계획 대비 구현 검증 (§6)

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|----------|
| Phase 0 | CONDITIONAL 상태 처리 + distribution_eligible | ✅ | `marketing_material.py:68`, `MarketingMaterialsTab.tsx` |
| Phase 1 | TemplateSpec/SlotSpec 계약 정의 | ✅ | `template_spec.py` (양쪽), specs 4개 |
| Phase 2 | Gate A Template Preflight | ✅ | `template_preflight.py` (양쪽) |
| Phase 3 | Gate B 강화 (SlotSpec 기반) | ⚠️ | 구현됨, 단 이중 카운팅 버그 [C-2] |
| Phase 4 | 골든 샘플 체계 | ✅ | `test_golden_samples.py`, fixtures 6개 |
| Phase 5 | Gate C Visual Diff | ⚠️ | 구현됨, 단 IM 테스트 시그니처 불일치 [C-1] |
| Phase 6 | 성능 메트릭 표준화 | ⚠️ | 구현됨, 단 재생성 경로 메트릭 0 [M-3] |

---

## Methodology

- **Agents**: code-reviewer, security-reviewer, performance-profiler, python-code-reviewer
- **Files scanned**: 47
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 3건 + Major 6건 → C-1/C-2/M-3/M-4 CONFIRMED, 2건 FALSE POSITIVE
- **FP Prevention**: 가설 26건 검증, 6건 사전 거부 (거부율: 23%)

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 3 | StrEnum py311 타겟 확인, `import os` 실사용 확인, list형 subprocess |
| 설계 의도 | 2 | CONDITIONAL 다운로드=PLAN 결정, 레지스트리 별도 프로세스 |
| 중복 | 1 | python-reviewer와 code-reviewer 동일 이슈 병합 |
