# Code Review — VDR Direct Upload (통합 리뷰 R2-R6)

> **Review Date**: 2026-03-06 11:06
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: VDR Direct Upload 다단계 자동 라우팅 — 13개 리뷰 관점 중 R1 미수행 관점 보충
> **Method**: 4-Agent Parallel Review + Cross-Verification + Priority Scoring
> **선행 리뷰**: `docs/code-review/20260306_1018_VDR_Direct_Upload_Code_Review.md` (R1 기본 리뷰, 12건)
> **R1 수정 검증**: 9/9건 올바르게 수정됨, 회귀 없음

## 리뷰 범위

| Round | 관점 | 에이전트 |
|-------|------|---------|
| R2 | 위협 모델링 & 공격 표면 (STRIDE) | R2+R6 에이전트 |
| R3 | 데이터 흐름 & 무결성, API 계약 & 호환성 | R3 에이전트 |
| R4 | 에러 처리 완전성, 관찰 가능성 & 디버깅 용이성 | R4+R5 에이전트 |
| R5 | 배포 안전성, 의존성 & 결합도 | R4+R5 에이전트 |
| R6 | 도메인 로직, 접근성 & UX, 인지 복잡도 | R2+R6 에이전트 |
| 검증 | R1 이슈 9건 수정 확인 | 수정 검증 에이전트 |

### 대상 파일

**백엔드 (deal-mgmt/):**
- `app/services/vdr_classification_service.py` — 2차 심사 서비스
- `app/routers/vdr.py` — VDR API 엔드포인트
- `app/services/vdr_service.py` — VDR CRUD 서비스
- `app/schemas/vdr.py` — Pydantic 스키마
- `app/models/vdr_document.py` — SQLAlchemy 모델
- `app/models/enums.py` — Enum 정의
- `migrations/versions/068_vdr_classification_columns.py` — 마이그레이션

**프론트엔드 (amic-platform/src/):**
- `modules/ma/components/vdr/VdrTab.tsx`
- `modules/ma/components/vdr/DirectUploadZone.tsx`
- `modules/ma/components/vdr/DirectUploadResultModal.tsx`
- `modules/ma/hooks/useVdr.ts`
- `modules/ma/types/vdr.ts`

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1 | HIGH: 1 | P0: 1 |
| Major | 3 | HIGH: 3 | P1: 3 |
| Moderate | 5 | HIGH: 1 / MEDIUM: 4 | P2: 5 |
| Minor | 12 | MEDIUM: 7 / LOW: 5 | P3: 12 |
| **Total** | **21** | HIGH: **5** / MEDIUM: **11** / LOW: **5** | P0: **1** / P1: **3** / P2: **5** / P3: **12** |

**교차 검증**: 3건 수행 (2+ 에이전트 동시 발견)
**중복 제거**: 원본 30건 → 병합 후 21건 (9건 중복)

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)

#### [INT-01] BackgroundTask 완전 실패 시 PENDING_REVIEW 영구 잔류 — Critical/HIGH (점수: 110, 교차 검증됨)

**발견**: R3 에이전트 + R4+R5 에이전트 (2개 에이전트 교차 확인)

**위치**: `deal-mgmt/app/routers/vdr.py:546-559`

**증거**:
```python
async def _run_secondary_classification(document_id, transaction_id):
    from app.core.database import async_session_factory
    async with async_session_factory() as db:
        try:
            result = await classify_document_by_content(db, document_id, transaction_id)
            logger.info("2차 심사 완료: doc=%s → %s", document_id, result)
        except Exception:
            logger.exception("2차 심사 실패: doc=%s", document_id)
            # ← PENDING_REVIEW 상태 전환 없음
```

**영향**: `async_session_factory()` 자체가 실패하거나(DB 연결 풀 소진), `classify_document_by_content` 내부의 commit이 실패하면 문서가 `PENDING_REVIEW` 상태로 영구 잔류. FE에서 "분류 중..." 스피너가 무한히 표시됨.

**수정 제안**:
```python
async def _run_secondary_classification(document_id, transaction_id):
    try:
        async with async_session_factory() as db:
            result = await classify_document_by_content(db, document_id, transaction_id)
            logger.info("2차 심사 완료: doc=%s → %s", document_id, result)
    except Exception:
        logger.exception("2차 심사 실패: doc=%s", document_id)
        try:
            async with async_session_factory() as fallback_db:
                stmt = select(VdrDocument).where(VdrDocument.id == document_id)
                doc = (await fallback_db.execute(stmt)).scalar_one_or_none()
                if doc and doc.classification_status == VdrClassificationStatus.PENDING_REVIEW:
                    doc.classification_status = VdrClassificationStatus.MANUAL_REVIEW
                    doc.manual_review_needed = True
                    await fallback_db.commit()
        except Exception:
            logger.exception("폴백 상태 업데이트도 실패: doc=%s", document_id)
```

---

### P1 — 스프린트 우선 (점수: 60-89)

#### [INT-02] FE/BE MIME 타입 화이트리스트 불일치 — Major/HIGH (점수: 80, 교차 검증됨)

**발견**: R3 + R4+R5 + R2+R6 에이전트 (3개 에이전트 교차 확인)

**위치**:
- BE: `deal-mgmt/app/routers/vdr.py:48-75` (28개 MIME 타입)
- FE: `amic-platform/src/modules/ma/types/vdr.ts:153-166` (12개 MIME 타입)

**증거**: BE에서 허용하지만 FE에서 차단되는 M&A 실사 핵심 파일 형식:
- `.hwp` (한글 문서) — `application/haansofthwp`, `application/x-hwp`
- `.eml`/`.msg` (이메일 증거) — `message/rfc822`, `application/vnd.ms-outlook`
- `.dwg`/`.dxf` (도면) — `image/vnd.dwg`, `application/dxf`
- `.json`, `.tar`, `.gz`, `.kml`, `.key` 등 11개 MIME 타입 누락

**영향**: DirectUploadZone의 `validateFiles()`에서 "허용되지 않는 파일 형식" 에러로 차단. `file input`의 `accept` 속성에도 해당 확장자 미포함으로 파일 탐색기에서도 선택 불가.

**수정 제안**: FE `VDR_CONSTRAINTS`의 `ALLOWED_MIME_TYPES`와 `ACCEPT_EXTENSIONS`를 BE와 동기화.

---

#### [INT-03] Direct Upload 성공 시 감사 로깅(Audit Logging) 부재 — Major/HIGH (점수: 70)

**위치**: `deal-mgmt/app/routers/vdr.py:567-677`

**증거**: `direct_upload` 핸들러에서 실패 시에만 `logger.warning`이 존재(라인 612, 649). 업로드 성공, 사용자 식별, 파일 수 등의 감사 로그가 없음.

**영향**: M&A VDR 문서는 법적 실사 자료. 누가 언제 어떤 파일을 업로드했는지 추적 불가 (STRIDE: Repudiation 위협).

**수정 제안**: 응답 반환 직전에 구조화된 감사 로그 추가:
```python
logger.info("Direct upload 완료: user=%s, txn=%s, total=%d, pending=%d",
            claims.email, txn_id, len(results), len(pending_doc_ids))
```

---

#### [INT-04] 2차 심사 DB commit 실패 시 명시적 롤백 부재 — Major/HIGH (점수: 70)

**위치**: `deal-mgmt/app/services/vdr_classification_service.py:148-153, 180-185, 196-200, 211-215`

**증거**: 4곳의 에러 핸들링에서 `doc.classification_status` 변경 후 `await db.commit()` 호출. commit 실패 시 명시적 rollback 없음.

```python
except Exception:
    doc.classification_status = VdrClassificationStatus.MANUAL_REVIEW
    doc.manual_review_needed = True
    await db.commit()  # ← 실패 시 롤백 없음
```

**영향**: `async with` 세션 컨텍스트가 암묵적 롤백을 수행하므로 데이터 오염 위험은 낮지만, commit 실패 원인 추적이 어려움.

**수정 제안**: 각 commit을 try/except로 감싸거나 함수 최상위에 종합 try/finally 추가.

---

### P2 — 개선 권장 (점수: 30-59)

#### [INT-05] 업로드 실패 파일이 사용자에게 보이지 않음 — Moderate/MEDIUM (점수: 52, 교차 검증됨)

**발견**: R4+R5 + R2+R6 + R4+R5 에이전트 (3개 에이전트 관련 이슈 발견)

**위치**: `deal-mgmt/app/routers/vdr.py:611-613, 648-650`

**증거**:
```python
except (ValueError, DocumentNotFoundError) as exc:
    logger.warning("Direct upload 1차 통과 파일 업로드 실패: %s — %s", filename, exc)
    continue  # 결과 목록에 포함 안 됨
```

**영향**: 10개 파일 업로드 시 2개 실패 → "8개 업로드됨"만 표시, 어떤 파일이 왜 실패했는지 알 수 없음. `_validate_upload`의 HTTPException은 전체 배치를 중단시킴.

**수정 제안**: `DirectUploadBatchResult`에 `failed_files: list[FailedFileInfo]` 필드 추가.

---

#### [INT-06] suggest-category API 호출 방식(body vs query) 및 응답 필드명 불일치 — Moderate/MEDIUM (점수: 42)

**위치**:
- BE: `deal-mgmt/app/routers/vdr.py:468-490` — `filename: str = Query(...)`
- FE: `amic-platform/src/modules/ma/hooks/useVdr.ts:287-297` — `{ filename }` POST body

**증거**: BE는 Query 파라미터(`?filename=...`)로 기대하지만, FE는 POST body(`{ filename }`)로 전송. 응답 필드명도 불일치: BE `suggested_category`/`suggested_folder_id` vs FE `category`/`folder_name`.

**영향**: `useSuggestVdrCategory` 호출 시 422 에러 발생. 현재 이 기능이 UI에서 사용되지 않으므로 사용자 영향은 없으나, 향후 통합 시 문제.

---

#### [INT-07] classification_status 이중 commit 구조 — Moderate/HIGH→MEDIUM (점수: 42)

**위치**: `deal-mgmt/app/routers/vdr.py:603-626, 638-664, 667`

**증거**: `auto_upload_document`/`upload_document` 내부에서 commit 후, 라우터에서 `classification_status` 설정 후 최종 commit. 중간에 예외 발생 시 `classification_status`가 NULL로 남을 수 있음.

**영향**: 현재 정상 동작하지만 트랜잭션 원자성이 보장되지 않음.

**수정 제안**: `upload_document`에 `classification_status` 파라미터 추가, 또는 내부 commit을 flush로 변경.

> ⚠️ 에이전트가 "정상 동작"으로 판단하여 신뢰도를 MEDIUM으로 하향 조정함.

---

#### [INT-08] classify_document_by_content에서 transaction_id WHERE 절 부재 — Moderate/HIGH→MEDIUM (점수: 42)

**위치**: `deal-mgmt/app/services/vdr_classification_service.py:134`

**증거**:
```python
stmt = select(VdrDocument).where(VdrDocument.id == document_id)
# transaction_id 조건 없음
```

**영향**: 현재 `_run_secondary_classification`에서만 호출되고, 라우터에서 이미 소유권 검증 완료. 방어 심층(defense-in-depth) 관점의 개선.

> ⚠️ 내부 전용 호출 경로이므로 신뢰도를 MEDIUM으로 하향 조정함.

---

#### [INT-09] LLM API 호출 타임아웃 미설정 — Moderate/MEDIUM (점수: 42)

**위치**: `deal-mgmt/app/services/vdr_classification_service.py:179`

**증거**:
```python
raw_response = await llm.call(system=system_prompt, user=user_prompt)
# 타임아웃 없음
```

**영향**: LLM API 네트워크 지연 시 BackgroundTask 워커 스레드 무기한 점유. Azure VM E2s_v3 (2 vCPU) 환경에서 다중 2차 심사 시 병목 가능.

**수정 제안**: `asyncio.wait_for(llm.call(...), timeout=60.0)` 적용.

---

### P3 — 저우선 (점수: <30)

| # | ID | 제목 | 심각도/신뢰도 | 점수 |
|---|-----|------|-------------|------|
| 10 | INT-10 | BackgroundTasks 동시 실행 무제한 (Semaphore 미적용) | Minor/MEDIUM | 12 |
| 11 | INT-11 | classification-status UUID 열거 가능성 | Minor/MEDIUM | 12 |
| 12 | INT-12 | Rate Limiter: 다중 파일 1건 카운트 (분당 400파일 가능) | Minor/MEDIUM | 12 |
| 13 | INT-13 | classification_status 상태 전이 라우터/서비스 분산 | Minor/MEDIUM | 12 |
| 14 | INT-14 | FE 폴링 에러 시 사용자 피드백 부재 (retry/onError 미설정) | Minor/MEDIUM | 12 |
| 15 | INT-15 | 1차/2차 심사 임계치 매직 넘버 (60점, 0.6 신뢰도) | Minor/MEDIUM | 12 |
| 16 | INT-16 | direct_upload 핸들러 인지 복잡도 (110줄, 7개 책임) | Minor/MEDIUM | 12 |
| 17 | INT-17 | 폴링 간격 5초 매직 넘버 | Minor/LOW | 6 |
| 18 | INT-18 | DirectUploadZone aria-disabled 미적용 | Minor/LOW | 6 |
| 19 | INT-19 | 2차 심사 로깅에 transaction_id 컨텍스트 누락 | Minor/LOW | 6 |
| 20 | INT-20 | _parse_llm_response 중첩 JSON 파싱 실패 가능성 | Minor/LOW | 6 |
| 21 | INT-21 | 마이그레이션 downgrade 데이터 손실 주석 미기재 | Minor/LOW | 6 |

---

## R1 수정 검증 결과

| 수정 ID | 원본 이슈 | 수정 상태 | 회귀 |
|---------|----------|----------|------|
| SEC-002 | LLM 프롬프트 인젝션 | ✅ 올바르게 수정됨 | 없음 |
| VDR-FE-01 | 무한 폴링 | ✅ 올바르게 수정됨 | 없음 |
| VDR-FE-02 | MIME 타입 검증 | ✅ 올바르게 수정됨 | 없음 |
| VDR-FE-03 | console.warn → toast | ✅ 올바르게 수정됨 | 없음 |
| VDR-FE-06 | 이중 제출 방지 | ✅ 올바르게 수정됨 | 없음 |
| SEC-006 | doc_ids 제한 | ✅ 올바르게 수정됨 | 없음 |
| W-01 | N+1 쿼리 | ✅ 올바르게 수정됨 | 없음 |
| W-02 | 배치 파일 제한 | ✅ 올바르게 수정됨 | 없음 |
| SEC-008 | 마스킹 패턴 보강 | ✅ 올바르게 수정됨 | 없음 |

---

## 잘 구현된 부분 (Positive Findings)

1. **BE↔FE 타입 계약 일관성**: `VdrClassificationStatus`, `DirectUploadBatchResult`, `ClassificationStatusItem` 등 핵심 타입이 BE/FE 양쪽에서 정확히 일치. Nullable 필드도 동일하게 처리.
2. **다단계 심사 아키텍처**: 1차(동기, 메타데이터) → 2차(비동기, LLM) 구조로 사용자 체감 속도와 분류 정확도 모두 만족.
3. **BackgroundTask 세션 격리**: `async_session_factory()`로 새 DB 세션 생성하여 요청 세션과 독립 동작.
4. **파일 업로드 다층 방어**: 확장자 화이트리스트 + MIME 교차 검증 + 경로 탐색 방지 + 파일 크기 이중 검증.
5. **인증/인가 일관성**: 모든 VDR 엔드포인트에 `get_jwt_claims` + `_get_and_authorize_txn` 적용.
6. **마이그레이션 크로스 DB 호환**: SQLite/PostgreSQL 분기 처리 올바름, `downgrade()` 실질적 롤백 SQL 포함.
7. **Rate Limiting**: `InMemoryRateLimiter` 분당 20건 적용.
8. **FE 폴링 자동 중지**: 모든 문서 분류 완료 시 `refetchInterval` → `false`.
9. **접근성 기반**: DirectUploadZone에 `role="button"`, `tabIndex={0}`, `aria-label`, 키보드 핸들링 구현.
10. **민감정보 보호**: 6종 마스킹 + XML 이스케이핑 + 프롬프트 인젝션 방어 3중 보안.

---

## 교차 검증 (Cross-Verification)

| 이슈 | 발견 에이전트 수 | 일치 판정 |
|------|---------------|----------|
| BackgroundTask PENDING_REVIEW 잔류 | 2 (R3 + R4+R5) | CONFIRMED |
| FE/BE MIME 화이트리스트 불일치 | 3 (R3 + R4+R5 + R2+R6) | CONFIRMED |
| 실패 파일 사용자 미노출 | 3 (R4+R5 + R2+R6, 2개 관점) | CONFIRMED |

---

## Methodology

- **Agents**: 수정 검증(1), R3 데이터 정합성(1), R4+R5 복원력/운영(1), R2+R6 위협/UX(1) — 총 4개 병렬
- **Files scanned**: BE 7개 + FE 5개 = 12개
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 자동 (동일 이슈 다중 에이전트 발견 시 병합 + 가산)
- **Deduplication**: 원본 30건 → 병합 후 21건 (중복 9건 제거)
- **Confidence adjustments**: 2건 하향 (INT-07, INT-08: 내부 호출 경로/정상 동작 확인으로 HIGH→MEDIUM)

## 권장 수정 순서

1. **즉시**: INT-01 (PENDING_REVIEW 영구 잔류 방지)
2. **P1 배치**: INT-02 (MIME 동기화) + INT-03 (감사 로깅) + INT-04 (commit 롤백)
3. **P2 개선**: INT-05 (실패 파일 노출) + INT-06 (API 계약 수정) + INT-09 (LLM 타임아웃)
4. **P3 백로그**: 나머지 12건
