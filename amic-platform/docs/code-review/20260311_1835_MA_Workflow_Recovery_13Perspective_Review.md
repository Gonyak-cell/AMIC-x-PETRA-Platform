# Code Review — MA 워크스페이스 운영 상태 복구 (5건 구현)

> **Review Date**: 2026-03-11 18:35
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 플랜 `crispy-churning-pine.md` 5건 구현 — IntegrityError 재시도, blocking_reasons, FINALIZING 리셋, 마케팅 자료 검증, NDA skipped_reasons
> **Method**: Review Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: ruff-check(✅ PASS) ruff-format(✅ PASS) pytest-collect(✅ 1719 tests)
> **Review Gates**: Backend(✅ available) Agent-Filtering(3개 에이전트 호출)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 2     | HIGH: 2                | P1: 2               |
| Moderate | 3     | HIGH: 1 / MEDIUM: 2   | P2: 1 / P3: 2       |
| Minor    | 1     | HIGH: 1                | P3: 1               |
| **Total**| **6** | HIGH: **4** / MEDIUM: **2** | P1: **2** / P2: **1** / P3: **3** |

**FP Prevention**: 가설 17건 검증, 10건 사전 거부 (거부율: 59%) | 교차 검증 2건 수행 (FP 제거: 0건)

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 2건 하향 조정 (Moderate → P3)

---

## Findings

### [R4-01] X-Skipped-Summary 한글 헤더 인코딩 에러 — [Major/HIGH] — Priority: P1

**파일**: `deal-mgmt/app/routers/nda_markups.py`, `deal-mgmt/app/routers/proxy.py`
**상태**: 🐛 **확정적 버그** (교차 검증 확인)

**문제**:
`skipped_reasons`에 수집되는 사유 문자열이 한글을 포함합니다:
```python
reason = f"항목 {i} (issue={issue_id}): {exc}"
```

이 문자열이 HTTP 응답 헤더 `X-Skipped-Summary`에 그대로 삽입됩니다:
```python
**({"X-Skipped-Summary": "; ".join(skipped_reasons)} if skipped_reasons else {}),
```

HTTP 헤더는 RFC 7230에 의해 US-ASCII만 허용합니다. Starlette/uvicorn은 `latin-1`으로 인코딩하므로, 한글 포함 시 `UnicodeEncodeError` → **500 Internal Server Error**가 발생합니다.

**영향**: NDA redline에서 이슈가 1건이라도 skip되면 **100% 500 에러** 발생.

**검증 추적**:
- Agent B(R4 Resilience)가 최초 발견
- 교차 검증: Starlette 소스 확인 → `latin-1` 인코딩 확정
- SC-1(코드 확인) ✓, SC-2(재현 경로) ✓, SC-3(영향도) ✓

**수정 권장**:
```python
# 옵션 A: URL 인코딩
from urllib.parse import quote
headers["X-Skipped-Summary"] = quote("; ".join(skipped_reasons))

# 옵션 B: 헤더에는 카운트만, 상세는 응답 본문으로
headers["X-Skipped-Count"] = str(len(skipped_reasons))
```

**우선순위 점수**: 70 × 1.0 + 15 (verifier 확인) = **85**

---

### [R2-01] reset_stuck_model 감사 로깅 누락 — [Major/HIGH] — Priority: P1

**파일**: `deal-mgmt/app/services/financial_model_service.py`
**상태**: 교차 검증 확인 (R5-03과 교차 발견)

**문제**:
기존 상태 변경 함수들(`create_financial_model`, `regenerate_financial_model`)은 모두 `audit_service.record()`를 호출하여 감사 로그를 남깁니다. 그러나 새로 추가된 `reset_stuck_model()`은 감사 로깅이 없습니다.

수동 리셋은 운영 이벤트로서 감사 추적이 **필수**입니다.

**현재 코드**:
```python
async def reset_stuck_model(
    db: AsyncSession,
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> FinancialModel:
    # ... 상태 변경 ...
    fm.status = FinancialModelStatus.PENDING_REVIEW
    fm.error_message = "관리자에 의해 수동 리셋됨"
    await db.commit()
    # ❌ audit_service.record() 호출 없음
```

**검증 추적**:
- Agent A(R2 Security)가 최초 발견
- Agent B(R5 Operations)가 독립적으로 동일 이슈 발견 (R5-03)
- 교차 검증: 2개 에이전트 일치 → 신뢰도 보강

**수정 권장**:
1. 함수 시그니처에 `actor_email: str` 파라미터 추가
2. 라우터에서 `claims.email` 전달
3. `await audit_service.record(db, ...)` 호출 추가

**우선순위 점수**: 70 × 1.0 + 10 (교차 검증) + 15 (verifier 확인) = **95** → P0 자격이나, 데이터 유실 아닌 로깅 누락이므로 P1 유지

---

### [R3-04] blocking_reasons에 prerequisites 미충족 사유 미포함 — [Moderate/HIGH] — Priority: P2

**파일**: `deal-mgmt/app/services/workflow_engine.py`

**문제**:
`all_met=false`(prerequisites 미충족)인 경우 `blocking_reasons`가 빈 리스트로 반환됩니다:

```python
blocking_reasons: list[str] = []
if not can_advance:
    if not all_met:
        pass  # ← prerequisites 리스트로 충분하다는 판단
    elif next_phase is None:
        blocking_reasons.append("마지막 단계입니다")
    elif txn.status != TransactionStatus.ACTIVE:
        blocking_reasons.append(f"거래 상태가 {txn.status.value}입니다 (ACTIVE 필요)")
```

FE에서 `blocking_reasons`를 표시하는 UI가 있으므로, prerequisites 미충족 시에도 사유가 표시되면 UX가 개선됩니다.

**영향**: 기능 장애 없음, UX 불완전.

**수정 권장**:
```python
if not all_met:
    unmet = [p["label"] for p in prerequisites if not p["met"]]
    blocking_reasons.append(f"미충족 항목: {', '.join(unmet)}")
```

**우선순위 점수**: 40 × 1.0 = **40**

---

### [R4-02] reset_stuck_model과 Celery 태스크 충돌 가능성 — [Moderate/HIGH] — Priority: P2 (참고)

**파일**: `deal-mgmt/app/services/financial_model_service.py`

**문제**:
리셋 시점에 Celery 워커가 아직 모델을 처리 중이면, 리셋 후에도 워커가 상태를 다시 변경할 수 있습니다 (race condition).

**실제 위험도**: 낮음. Celery 태스크가 실패하여 멈춘 경우에만 리셋을 사용하므로, 실제로 워커가 살아있는 상태에서 리셋할 가능성은 극히 낮습니다.

**수정 권장** (선택적):
- Celery `AsyncResult.revoke()` 호출 후 리셋
- 또는 UI에 "태스크가 실행 중이 아닌지 확인하세요" 경고 추가

**우선순위 점수**: 40 × 1.0 = **40** (실제 위험 낮아 참고 사항)

---

### [R3-01] IntegrityError 재시도 모니터링 로깅 권장 — [Moderate/MEDIUM] — Priority: P3

**파일**: `deal-mgmt/app/services/deal_setup_service.py`

**문제**:
IntegrityError 재시도 패턴이 정상 동작하지만, 재시도 발생 시 로깅이 `logger.warning`으로만 기록됩니다. 운영 환경에서 재시도 빈도를 모니터링하려면 structured logging이 권장됩니다.

**영향**: 기능 장애 없음, 운영 가시성 개선.

**우선순위 점수**: 40 × 0.6 = **24**

---

### [R3-03/R5-01] 서비스 레이어 HTTPException 직접 raise — [Minor/HIGH] — Priority: P3

**파일**: `deal-mgmt/app/services/financial_model_service.py`, `deal-mgmt/app/services/marketing_material_service.py`

**문제**:
서비스 레이어에서 `HTTPException`을 직접 raise합니다. 이상적으로는 서비스 레이어는 도메인 예외를 raise하고 라우터에서 HTTP 예외로 변환하는 것이 계층 분리에 적합합니다.

**현실**: 기존 코드베이스 전체(`deal-mgmt`)가 이 패턴을 사용하고 있으므로, **기존 관례와 일관성**을 유지하는 것이 맞습니다. 리팩토링은 별도 작업으로 진행해야 합니다.

**영향**: 없음 (기존 패턴 준수).

**우선순위 점수**: 20 × 1.0 = **20**

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)
1. **[R4-01]** [Major/HIGH]: X-Skipped-Summary 한글 헤더 → UnicodeEncodeError 500 (점수: 85, 확정적 버그)
2. **[R2-01]** [Major/HIGH]: reset_stuck_model 감사 로깅 누락 (점수: 95→P1, 교차 검증)

### P2 — 개선 권장 (점수: 30-59)
3. **[R3-04]** [Moderate/HIGH]: blocking_reasons 미충족 사유 비어 있음 (점수: 40)
4. **[R4-02]** [Moderate/HIGH]: Celery 태스크 충돌 가능성 (점수: 40, 참고)

### P3 — 저우선 (점수: <30)
5. **[R3-01]** [Moderate/MEDIUM ⚠️]: IntegrityError 재시도 structured logging (점수: 24, 신뢰도 하향)
6. **[R3-03/R5-01]** [Minor/HIGH]: 서비스 레이어 HTTPException (점수: 20, 기존 패턴)

---

## 계획 대비 구현 검증 (§6)

| # | 계획된 항목 | 구현 상태 | 검증 근거 (파일:라인) |
|---|-----------|---------|---------------------|
| 1 | AI 확정 경로 IntegrityError 재시도 | ✅ 완료 | `deal_setup_service.py` try/except IntegrityError + 409 핸들링 |
| 2 | phase-status에 blocking_reasons 추가 | ✅ 완료 (⚠️ R3-04) | `workflow.py` 필드 + `workflow_engine.py` 로직 + FE 타입/UI |
| 3 | 재무모델 FINALIZING 멈춤 복구 | ✅ 완료 (⚠️ R2-01) | `financial_model_service.py` reset + `financial_models.py` 엔드포인트 |
| 4 | 마케팅 자료 필수 요소 사전 검증 | ✅ 완료 | `marketing_material_service.py` _validate_prerequisites + 422 |
| 5 | NDA redline 부분 실패 응답 반영 | ✅ 완료 (🐛 R4-01) | `nda_analysis_service.py` + `nda_markups.py` + `proxy.py` |

**계획 항목 5/5 구현 완료.** 2건의 보완 필요 이슈 발견 (R4-01 버그, R2-01 감사 로깅).

---

## Methodology

- **Agents**: R2 Security + R3 Data Integrity (Agent A), R4 Resilience + R5 Operations (Agent B), R6 Business + §1-§4 + §6 Plan (Agent C)
- **Files scanned**: 10개 (BE 8 + FE 2)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Major 2건 수행 → 2건 모두 CONFIRMED
- **Backend availability**: deal-mgmt(✅ available)

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 17건
- 거부된 가설 (사전 제거): 10건
- 보고된 이슈: 6건 (중복 병합 후)
- 거부율: 59%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 기존 패턴 일관 | 4 | "서비스에서 HTTPException" → 기존 코드 전체가 동일 패턴 |
| 범위 외 | 3 | FE 접근성, 국제화 등 이번 구현 범위 외 |
| 반증됨 | 2 | "필드 누락" → Read로 확인 시 이미 존재 |
| 신뢰도 불충분 | 1 | 증거 약함 |

---

## 수정 권장 우선순위

1. **즉시 수정 (R4-01)**: `X-Skipped-Summary` 헤더를 ASCII-safe하게 변경 — skip 발생 시 500 에러 방지
2. **빠른 보완 (R2-01)**: `reset_stuck_model`에 감사 로깅 추가 — 운영 추적성 확보
3. **선택적 개선 (R3-04)**: `blocking_reasons`에 미충족 항목 사유 포함 — UX 개선
