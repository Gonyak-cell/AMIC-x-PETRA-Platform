# [type] FDD industry 타입 단언 제거

> 2026-02-23 12:15:00
> 파일: `amic-platform/src/modules/docs/hooks/useFDDDocuments.ts`

## 문제

`useFDDDocuments.ts:30`에서 `industry: body.industry as Deal["industry"]` 타입 단언 사용.

- `body.industry`는 `string | undefined` — TypeScript가 타입 안전성을 보장하지 않음
- `Deal["industry"]`는 실제로 `IndustryId` (유니온 타입)로 정의되어 있어, 잘못된 값 전달 시 런타임 불일치 가능

## 수정

```typescript
// 수정 전
industry: body.industry as Deal["industry"],

// 수정 후
import { isIndustryId } from "@/types/industry";
// ...
industry: body.industry && isIndustryId(body.industry) ? body.industry : undefined,
```

기존 `isIndustryId()` 타입 가드(`@/types/industry`) 재사용으로 런타임 검증 추가.

## 관련 이슈

- D-003 (VCP v1.1 리뷰 Moderate/MEDIUM → 수정)
- 관련 리뷰: `docs/code-review/20260223_1214_Docs_MA_Full_Code_Review.md`
