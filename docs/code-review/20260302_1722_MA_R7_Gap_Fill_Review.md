# Code Review — Round 7: Gap-Fill Review (R5~R6 미다룬 관점)

> **Review Date**: 2026-03-02 17:22
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: R5~R6 수정 코드 + 미다룬 3개 관점 (Performance, Data Integrity, Fix Correctness)
> **Quality Gates**: ruff(✅) tsc(✅) pytest(15/15 ✅)
> **Agents**: Performance, Data Integrity/Migration, R5-R6 Fix Correctness Audit

## Summary

| Severity | Count | 수정됨 | 미수정 (설계적) |
|----------|-------|--------|---------------|
| Critical | 0 | - | - |
| Major | 8 | 3 | 5 (의도적 설계 또는 수정 불가) |

## 수정된 이슈 (3건)

### [R7-BLOB-01] `delete_blob` — Azure SDK `ResourceNotFoundError` 직접 catch
- **변경 전**: 문자열 매칭 (`"not found" in str(exc).lower()`)
- **변경 후**: `from azure.core.exceptions import ResourceNotFoundError` + `except ResourceNotFoundError`
- **파일**: `blob_storage.py:169-174`

### [R7-PERF-02] `useTransactions` — `staleTime: 30_000` 추가
- **변경 전**: `staleTime` 없음 (기본 0 → 매번 refetch)
- **변경 후**: 30초 staleTime → 불필요한 refetch 방지
- **파일**: `useTransactions.ts:42`

### [R7-PERF-03] `approval_summary` — COUNT GROUP BY 최적화
- **변경 전**: 전체 ORM 객체 로드 → Python에서 카운트
- **변경 후**: `SELECT status, COUNT(*) ... GROUP BY status` → DB 레벨 집계
- **파일**: `approvals.py:68-76`

## 미수정 이슈 (5건 — 설계적 결정 또는 수정 불가)

| ID | 이슈 | 사유 |
|----|------|------|
| R7-PERF-01 | TWP 4개 훅 무조건 실행 | 탭 배지 카운트용 — 제거 시 UI 빈 배지 |
| R7-FE-01 | MODEL_TO_QK 7개 미사용 키 | 향후 확장 대비 forward-looking — 기능 영향 없음 |
| R7-MIG-01 | Migration 053 스냅샷 부재 | 이미 실행 완료된 마이그레이션 — 소급 수정 불가 |
| R7-PERF-04 | my_pending_approvals Python 필터링 | JSONB SQL 필터 변환은 별도 세션 과제 |
| R7-PERF-05 | fm_tasks event loop 매번 생성 | Celery async 실행 구조적 한계 — 안전성 우선 |
