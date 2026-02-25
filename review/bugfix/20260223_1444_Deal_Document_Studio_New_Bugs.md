# Deal Document Studio 신규 버그 수정

> 작성일: 2026-02-23 14:44:00
> 리뷰 범위: Deal Document Studio 전체 (프론트엔드 + 백엔드 불일치 검증)

---

## 배경

Session 33에서 기존 리뷰(20260223_1349)의 15개 이슈가 수정됐다고 보고됨.
전체 코드를 직접 재탐색하여 (1) 허위 양성 검증, (2) 신규 누락 버그 발견.

---

## 기존 리뷰 허위 양성 검증 결과

**15개 이슈 전체 — 허위 양성 0건, 모두 정상 구현 확인.**

| 이슈 ID | 내용 | 확인 위치 | 결론 |
|---------|------|---------|------|
| BE-SEC-01 | Path Traversal 방어 | `legal_documents.py:23-25` | ✅ |
| BE-SEC-02 | 거래 소유권 검증 | `_get_and_authorize_txn()` | ✅ |
| BE-VALID-01 | 템플릿 존재 사전 검증 | service 내 FAILED 처리 | ✅ |
| BE-VALID-02 | Pydantic 날짜·범위 검증 | 5가지 타입별 스키마 | ✅ |
| FE-A11Y-01 | 폼 레이블 연결 | `htmlFor="legal-doc-title"` | ✅ |
| FE-A11Y-02 | 선택 상태 aria-label | `aria-label` 추가 확인 | ✅ |
| FE-TYPE-01 | 타입 안전성 | `LegalParamsForm` 타입별 분기 | ✅ |
| FE-ERR-01 | API 에러 메시지 전달 | `extractErrorDetail()` | ✅ |
| FE-UX-01 | GENERATING 폴링 | `refetchInterval` 3초 | ✅ |
| BE-HTTP-01 | HTTP 409→400 | `DocumentNotReadyError` → 400 | ✅ |
| BE-ERR-01 | 예외 레이어 분리 | 커스텀 예외 클래스 | ✅ |
| BE-PERF-01 | DB 인덱스 | Migration 008, 3개 인덱스 | ✅ |
| BE-TEST-01 | 경계 테스트 | Pydantic 검증 7개 테스트 | ✅ |
| BE-OPS-01 | 파일 정리 스크립트 | `scripts/cleanup_old_files.py` | ✅ |

---

## 신규 발견 버그 및 수정

### BUG-1: 다운로드 URL 프록시 미사용 🔴

**심각도**: Critical (개발 환경 다운로드 기능 완전 불가)

**근본 원인 분석**:
```
vite.config.ts proxy 규칙:
  /api/ma → http://localhost:8003 (deal-mgmt)
  rewrite: /api/ma/... → /api/v1/...

getLegalDocDownloadUrl 기존 코드:
  ${VITE_MA_API_URL ?? ""}/api/v1/transactions/...

VITE_MA_API_URL이 미설정이면:
  /api/v1/transactions/... → vite proxy 규칙 없음 → 404
```

**영향 파일**: [useLegalDocuments.ts:112-114](../../amic-platform/src/modules/docs/hooks/useLegalDocuments.ts#L112)

**수정 내용**:
```typescript
// Before
export function getLegalDocDownloadUrl(txnId: string, docId: string): string {
  return `${import.meta.env.VITE_MA_API_URL ?? ""}/api/v1/transactions/${txnId}/legal-documents/${docId}/download`;
}

// After
export function getLegalDocDownloadUrl(txnId: string, docId: string): string {
  return `/api/ma/transactions/${txnId}/legal-documents/${docId}/download`;
}
```

**프로덕션 호환성**: Nginx에서 동일하게 `/api/ma` prefix를 deal-mgmt로 라우팅하면 됨 (현재 설정과 동일).

---

### BUG-2: txnId 없을 때 생성 버튼 비활성화 미처리 ⚠️

**심각도**: Minor (기능 오동작은 아니나 UX 혼란)

**증상**:
- `StudioHomePage`에서 법률 문서 유형 카드 클릭 → `/docs/legal/new?type=SPA` (txnId 없음)
- Step 2 "문서 생성" 버튼이 활성화 상태
- 클릭해도 아무 반응 없음 (`handleGenerate`에서 `!txnId` 체크 후 early return)
- 경고 메시지는 표시되나 버튼은 disabled 아님

**영향 파일**: [CreateLegalDocumentPage.tsx:297](../../amic-platform/src/modules/docs/pages/CreateLegalDocumentPage.tsx#L297)

**수정 내용**:
```typescript
// Before
disabled={createMut.isPending}

// After
disabled={createMut.isPending || !txnId}
```

---

## 검증 결과

- **수정 파일**: 2개
- **백엔드 변경**: 없음
- **DB 마이그레이션**: 불필요
- **기존 기능 영향**: 없음
