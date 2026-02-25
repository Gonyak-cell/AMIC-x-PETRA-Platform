# [bugfix] Docs + MA 전체 코드 리뷰 수정 내역

> 2026-02-23 12:15:00
> 브랜치: `feat/ma-workflow`
> 리뷰 리포트: `docs/code-review/20260223_1214_Docs_MA_Full_Code_Review.md`

---

## 수정 1: URL 파라미터 타입 가드 (D-001)

**파일**: `CreateDocumentPage.tsx:127`

```typescript
// 수정 전
const typeParam = searchParams.get("type") as DocumentType | null;

// 수정 후
const _typeRaw = searchParams.get("type");
const typeParam: DocumentType | null =
  _typeRaw === "teaser" || _typeRaw === "im" || _typeRaw === "fdd"
    ? _typeRaw
    : null;
```

잘못된 URL 파라미터(`?type=invalid`)가 들어와도 안전하게 `null` 처리.

---

## 수정 2: FDD 에러 메시지 누락 (D-006)

**파일**: `CreateDocumentPage.tsx:398-401`

```typescript
// 수정 전
} catch {
  if (formData.docType !== "fdd") {
    toast.error("문서 생성에 실패했습니다");
  }
}

// 수정 후
} catch {
  toast.error("문서 생성에 실패했습니다");
}
```

FDD 문서 생성 실패 시에도 사용자에게 에러 메시지 표시.

---

## 수정 3: Orphan Deal 에러 추적 개선 (D-004)

**파일**: `useFDDDocuments.ts:44-47`

Deal 생성 성공 후 ReportVersion 생성 실패 시, `deal.id`를 포함한 구체적 에러 메시지 출력:

```typescript
try {
  const { data } = await fddApi.post<ReportVersion>(...);
  version = data;
} catch (versionError) {
  console.error("[useFDDDocuments] 보고서 버전 생성 실패, deal.id=", deal.id, versionError);
  throw new Error(
    `FDD 버전 생성에 실패했습니다 (deal.id: ${deal.id}). 관리자에게 문의해 주세요.`,
  );
}
```

---

## 수정 4: MA 훅 성공 토스트 불일치 (m-R002~R004 + DD)

4개 훅의 `onSuccess` 콜백에 성공 토스트 추가:

| 파일 | 훅 | 추가된 토스트 |
|------|----|------------|
| `useTransactions.ts` | `useUpdateBuyer` | `"매수자 정보가 수정되었습니다."` |
| `useRisks.ts` | `useUpdateRisk` | `"리스크 항목이 수정되었습니다."` |
| `useCompliance.ts` | `useUpdateCompliance` | `"컴플라이언스 항목이 수정되었습니다."` |
| `useDDChecklist.ts` | `useUpdateDDChecklistItem` | `"체크리스트 항목이 수정되었습니다."` |

---

## 수정 5: NDA 모달 취소 시 폼 초기화 (ISSUE-009)

**파일**: `TransactionWorkspacePage.tsx:2854`

```typescript
// 수정 전
onClick={() => setShowNdaModal(false)}

// 수정 후
onClick={() => {
  setShowNdaModal(false);
  setNdaForm({ buyer_candidate_id: "", nda_type: "MUTUAL" });
}}
```

---

## 수정 6: 안정적 key prop (ISSUE-005)

**파일**: `TransactionWorkspacePage.tsx:2454`

```typescript
// 수정 전
{approval.approvers.map((a, i) => (
  <Badge key={i} ...>

// 수정 후
{approval.approvers.map((a) => (
  <Badge key={a.email} ...>
```

---

## 수정 7: DashboardPage 테스트 업데이트

**파일**: `src/pages/__tests__/DashboardPage.test.tsx`

퀵액션 레이블이 "New IM" → "New Document"로 변경되어 테스트 업데이트.

---

## 미수정 (이월)

- `AIRiskFlag.risk_level` 타입 (백엔드 스키마 확인 필요)
- `TransactionWorkspacePage` 탭별 선택적 로드 (아키텍처 리팩토링)
- 나머지 4개 모달 취소 폼 초기화 (Engagement, Member, Buyer, Bid, DD)
- 필터 버튼 ARIA 접근성 개선
