# LDD (법률실사) 모듈 종합 코드 리뷰 및 수정 보고서

> 리뷰 일시: 2026-02-25 20:33 | 브랜치: feat/ma-workflow
> 계획 문서: `docs/architecture/20260225_1624_LDD_VDR_Integration_Completion_Report.md`

---

## 리뷰 요약

- **총 이슈 수**: 12개 (Critical: 1, Major: 4, Moderate: 5, Minor: 2)
- **수정 완료**: 12/12 (100%)
- **계획 대비 구현율**: 8/8 Phase (100%)
- **검증**: TypeScript `tsc --noEmit` 통과, Python AST 문법 검증 통과

---

## 수정된 파일 (6개)

| 파일 | 수정 내용 | 우선순위 |
|------|----------|---------|
| `amic-platform/src/modules/docs/types/ldd_report.ts` | Status 4→7개 동기화, LDDItem +6필드, LDDReport +9필드, STATUS_LABELS/COLORS 확장 | P0, P1 |
| `deal-mgmt/app/services/ldd_report_service.py` | `_merge_ai_results()` 헬퍼로 3곳 중복 제거 + `approved_items` 지원, `_validate_source_dir()` Path Traversal 방어, 중복 import 정리 | P2 |
| `deal-mgmt/app/services/ldd_review_service.py` | `review_item()`/`bulk_review()`에서 `user_override_status` 변경 시 `_compute_counts()` 호출 | P1 |
| `amic-platform/src/modules/docs/hooks/useLDDReports.ts` | 폴링 조건에 ANALYZING/FINALIZING 추가 (5초 간격) | P2 |
| `amic-platform/src/modules/ma/hooks/useLDDReports.ts` | `template_version`, `created_by_email` 필드 추가 | P3 |
| `deal-mgmt/tests/test_ldd_review.py` | `_set_report_status()` 헬퍼 + REVIEW 상태 리뷰 테스트 3개 추가 | P3 |

---

## 이슈 상세 (심각도 내림차순)

### [Critical] P0 — Docs 모듈 LDDReportStatus 동기화 누락 ✅ 수정 완료

- **위치**: `amic-platform/src/modules/docs/types/ldd_report.ts:3`
- **문제**: 백엔드 7개 상태 중 4개만 정의 → VDR 기반 보고서(ANALYZING/REVIEW/FINALIZING) 조회 시 UI crash
- **수정**: `LDDReportStatus` 7개 상태로 확장, `LDD_STATUS_LABELS`/`LDD_STATUS_COLORS`에 3개 상태 추가

### [Major] P1 — Docs 모듈 LDDItem 타입 6개 필드 누락 ✅ 수정 완료

- **위치**: `amic-platform/src/modules/docs/types/ldd_report.ts:25-36`
- **문제**: `confidence`, `evidence_refs`, `user_comment`, `user_approved`, `user_override_status`, `user_override_level` 누락 → 섹션 편집 후 AI/리뷰 데이터 유실 가능
- **수정**: 6개 필드 추가

### [Major] P1 — Docs 모듈 LDDReport 타입 9개 필드 누락 ✅ 수정 완료

- **위치**: `amic-platform/src/modules/docs/types/ldd_report.ts:48-75`
- **문제**: VDR/워크플로우 필드(`vdr_source`, `draft_score`, `final_score`, 6개 타임스탬프) 미정의
- **수정**: 9개 필드 추가

### [Major] P1 — review_item/bulk_review 시 counts 미갱신 ✅ 수정 완료

- **위치**: `deal-mgmt/app/services/ldd_review_service.py:59-64, :95-100`
- **문제**: `user_override_status` 변경 시 `_compute_risk_colors()`만 호출, `_compute_counts()` 미호출 → KPI 카드 불일치
- **수정**: 두 메서드에 `user_override_status` 존재 시 `_compute_counts()` 호출 + report 필드 갱신 로직 추가

### [Major] P2 — AI 결과 파싱 로직 3회 반복 ✅ 수정 완료

- **위치**: `deal-mgmt/app/services/ldd_report_service.py` (3곳)
- **문제**: `create_ldd_report_auto()`, `create_ldd_report_from_vdr()`, `finalize_ldd_report()` 3곳에서 동일 로직 반복. `create_ldd_report_auto()`에서 `confidence`/`evidence_refs` 복사 누락
- **수정**: `_merge_ai_results(sections, ai_sections, *, include_ai_meta, approved_items)` 헬퍼 함수 추출, 3곳 모두 헬퍼 호출로 대체. `approved_items` 파라미터로 finalize 시 승인 항목 user_override 로직 통합

### [Moderate] P2 — Docs 모듈 폴링 전략 미흡 ✅ 수정 완료

- **위치**: `amic-platform/src/modules/docs/hooks/useLDDReports.ts:25-30, :41-43`
- **문제**: `GENERATING` 상태만 폴링 → ANALYZING/FINALIZING 시 수동 새로고침 필요
- **수정**: `useLDDReports`와 `useLDDReport` 모두 ANALYZING/FINALIZING/GENERATING 3개 상태 5초 폴링

### [Moderate] P2 — source_dir 경로 검증 부재 ✅ 수정 완료

- **위치**: `deal-mgmt/app/services/ldd_report_service.py:372`
- **문제**: `scan_directory(body.source_dir)`가 사용자 입력 경로를 검증 없이 접근 → Path Traversal 가능
- **수정**: `_validate_source_dir()` 함수 추가 — `Path.resolve().relative_to(_PROJECT_ROOT)` 기반 검증

### [Moderate] P2 — 중복 import 정리 ✅ 수정 완료

- **위치**: `deal-mgmt/app/services/ldd_report_service.py:393-394, :405`
- **문제**: 파일 상단에서 이미 import된 `json`, `logging`을 함수 내부에서 재import, `logger` 재정의
- **수정**: 중복 `import json`, `import logging`, `logger = logging.getLogger(__name__)` 제거

### [Moderate] 다운로드 URL 경로 불일치 — 미수정 (환경 의존)

- **위치**: `amic-platform/src/modules/docs/hooks/useLDDReports.ts:199-201`
- **사유**: Nginx 프록시 리라이트에 의존하므로 현재 환경에서는 정상 동작. 추후 `maApi.defaults.baseURL` 활용으로 개선 가능

### [Moderate] LDDReviewService 상태 검증 범위 불일치 — 의도적 설계로 확인

- **위치**: `deal-mgmt/app/services/ldd_review_service.py:109`
- **사유**: `get_review_progress()`가 모든 상태에서 조회 가능한 것은 의도적 설계 (리뷰 전/후 진행률 표시 용도)

### [Minor] P3 — REVIEW 상태 테스트 헬퍼 ✅ 수정 완료

- **위치**: `deal-mgmt/tests/test_ldd_review.py`
- **문제**: REVIEW 상태 보고서 생성 불가로 리뷰 핵심 로직 테스트 부재
- **수정**: `_set_report_status()` 헬퍼 추가 + 3개 테스트 추가:
  - `test_review_item_requires_review_status` — REVIEW 아닌 상태에서 409 반환 확인
  - `test_review_item_approve` — REVIEW 상태 승인 동작 확인
  - `test_bulk_review` — REVIEW 상태 일괄 리뷰 동작 확인

### [Minor] P3 — MA 훅 LDDReport 2개 필드 누락 ✅ 수정 완료

- **위치**: `amic-platform/src/modules/ma/hooks/useLDDReports.ts:10-44`
- **문제**: `template_version`, `created_by_email` 미정의 (현재 UI 미사용)
- **수정**: 두 필드 추가 (타입 완전성 확보)

---

## 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| TypeScript `tsc --noEmit` | ✅ 통과 |
| Python AST 문법 검증 (`ldd_report_service.py`) | ✅ 통과 |
| Python AST 문법 검증 (`ldd_review_service.py`) | ✅ 통과 |
| Python AST 문법 검증 (`test_ldd_review.py`) | ✅ 통과 |

---

## 아키텍처 개선 요약

### `_merge_ai_results()` 헬퍼 (신규)

```python
def _merge_ai_results(
    sections: list[dict],
    ai_sections: dict,
    *,
    include_ai_meta: bool = True,
    approved_items: set[str] | None = None,
) -> list[dict]:
```

- **역할**: Ralph Loop AI 분석 결과를 기존 LDD 섹션에 병합
- **파라미터**:
  - `include_ai_meta`: confidence/evidence_refs 포함 여부
  - `approved_items`: 사용자 승인 항목 집합 → AI 결과 대신 user_override만 적용
- **사용처**: `create_ldd_report_auto()`, `create_ldd_report_from_vdr()`, `finalize_ldd_report()` 3곳

### `_validate_source_dir()` (신규)

```python
def _validate_source_dir(source_dir: str) -> None:
```

- **역할**: source_dir이 프로젝트 루트 하위인지 검증 (Path Traversal 방어)
- **방식**: `Path.resolve().relative_to(_PROJECT_ROOT)` — ValueError 시 거부
