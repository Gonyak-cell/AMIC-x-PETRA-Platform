# FDD 자동 분석 & 체크리스트 코드 리뷰

> 리뷰 일시: 2026-02-25 16:10
> 대상: Phase 1~6 구현 전체 (모델/서비스/API/렌더러/프론트엔드/테스트)
> 방법: 3개 병렬 Explore 에이전트 전수 탐색 + Plan 에이전트 실제 코드 대조 검증

---

## 검증 결과 요약

| # | 문제 | 판정 | 심각도 | 수정 |
|---|------|------|--------|------|
| 1 | `build_refined_report_ir()` 미구현 — checklist_id가 pptx/docx/json에서 무시됨 | PARTIAL | Medium | 향후 Phase |
| 2 | **Excel 렌더러 checklist_data 구조 불일치** — dict vs list[dict] | **TRUE** | **P0** | **수정 완료** |
| 3 | ChecklistRead 계산 필드가 항상 0 반환 | FALSE | — | — |
| 4 | VdrLinkRead의 upload_filename/folder_name DB 부재 | FALSE | — | — |
| 5 | **vdr-links 엔드포인트 deal_id 검증 누락 (IDOR)** | **TRUE** | **P0** | **수정 완료** |
| 6 | **보고서 버전 API 권한 체크 부재** | **TRUE** | **P1** | **수정 완료** |
| 7 | **ReportPage에서 checklist_id 미전달** | **TRUE** | **P1** | **수정 완료** |
| 8 | ChecklistReviewPage 분석 후 쿼리 무효화 누락 | PARTIAL | Low | **수정 완료** |
| 9 | ChecklistItemCard 상태 변경 시 correction 유실 | FALSE | — | — |
| 10 | test_excel_renderer.py 포맷 불일치 | TRUE | Medium | 문제 #2 수정으로 해결 |

**허위 양성 3개**: #3, #4, #9

---

## 허위 양성 검증 상세

### #3: ChecklistRead 계산 필드가 항상 0 (FALSE)

**주장**: `total_items=0`, `confirmed_count=0` 등이 기본값만 반환

**검증**: `checklist.py:71`에서 `**summary` unpacking으로 `get_checklist_summary()` 반환값이 주입됨
```python
return ChecklistRead(
    ...
    **summary,  # ← total_items, confirmed_count 등 정확히 오버라이드
)
```
**결론**: 정상 동작. Pydantic `default=0`은 fallback일 뿐.

### #4: VdrLinkRead upload_filename/folder_name (FALSE)

**주장**: 항상 None 반환, DB에 해당 컬럼 없음

**검증**: 스키마에 `Optional[str] = None`으로 선언. 향후 VDR 조인 시 채울 수 있는 확장 필드. 현재는 의도적으로 None.

### #9: ChecklistItemCard correction 유실 (FALSE)

**주장**: 상태 버튼 클릭 시 입력한 correction이 유실됨

**검증**: 로컬 state `correction`, `amount`가 `onUpdate(item.id, status, correction, amount)`에 전달. 상태 변경과 무관하게 현재 입력값 보존.

---

## 수정 내역

### Fix 1 (P0): Excel 렌더러 checklist_data 구조

**파일**: `fdd/backend/app/api/reports.py:110`

**원인**: `reports.py`가 `{"items": [...]}` dict를 전달하나, `render_excel_report()`는 `list[dict]` 기대 → 런타임 AttributeError

**수정**:
```python
# Before
xlsx_buffer = render_excel_report(report_ir, checklist_data=checklist_data)

# After
xlsx_buffer = render_excel_report(
    report_ir,
    checklist_data=checklist_data["items"] if checklist_data else None,
)
```

### Fix 2 (P0): IDOR 보안 — deal_id 소속 검증

**파일**: `fdd/backend/app/api/checklist.py`

**원인**: `get_item_vdr_links()`와 `update_checklist_item()`에서 item_id만으로 조회 → 다른 deal의 item 접근 가능

**수정**: 두 엔드포인트 모두에 `item.checklist.deal_id != deal_id` 검증 추가

### Fix 3 (P1): 보고서 버전 API 권한 체크

**파일**: `fdd/backend/app/api/reports.py`

**원인**: 4개 버전 관리 엔드포인트가 `Depends(get_current_user)` 사용 → 인증만 하고 권한 미검사

**수정**:
| 엔드포인트 | 변경 |
|-----------|------|
| `GET /versions` | `require_permission(Permission.DEAL_READ)` |
| `POST /versions` | `require_permission(Permission.REPORT_GENERATE)` |
| `PUT /versions/{v}/finalize` | `require_permission(Permission.REPORT_GENERATE)` |
| `GET /versions/{v}/download` | `require_permission(Permission.REPORT_DOWNLOAD)` |

### Fix 4 (P1): ReportPage checklist_id 전달

**파일**: `amic-platform/src/modules/fdd/pages/ReportPage.tsx`

**원인**: `generateMutation`이 `{ ...options }`만 전달 → checklist_id 미포함 → Excel 보고서에 체크리스트 시트 미생성

**수정**:
- `useChecklist(dealId)` 훅 import
- FINALIZED 체크리스트 존재 시 "Include Checklist Adjustments" 토글 UI 추가
- 토글 활성화 시 body에 `checklist_id` 포함

### Fix 5 (Low): ChecklistReviewPage 쿼리 무효화

**파일**: `amic-platform/src/modules/fdd/pages/ChecklistReviewPage.tsx`

**원인**: `handleRunAnalysis` 성공 시 toast만 표시 → React Query 캐시 미갱신

**수정**: `queryClient.invalidateQueries` 추가 (checklist + analysis 쿼리 키)

---

## 검증

- 백엔드: **47/47 테스트 통과** (`TESTING=true AUTH_ENABLED=false pytest`)
- 프론트엔드: **TypeScript 컴파일 에러 없음** (`tsc --noEmit`)
