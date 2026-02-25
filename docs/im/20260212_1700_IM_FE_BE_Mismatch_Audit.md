# IM 모듈 프론트엔드-백엔드 불일치 점검 보고서

> 최종 점검: 2026-02-12 16:59
> 점검 범위: IM 모듈 전체 (타입, 훅, 페이지, 컴포넌트 ↔ BE 스키마, 모델, 라우트, 서비스)

---

## 1. 점검 배경

이전 세션에서 IM 모듈 프론트엔드-백엔드 간 불일치 5건이 발견되어 수정 계획을 수립하였고,
이를 적용한 후 1차/2차 종합 점검을 통해 수정 상태를 검증하고 추가 불일치를 탐색하였다.

- **1차 점검**: 기존 5건 수정 확인 + 경미 불일치 2건 추가 발견 및 수정
- **2차 점검**: 3개 에이전트 병렬 투입 — 타입/스키마, 훅/라우트, 페이지/데이터 흐름을 필드 단위 전수 대조

---

## 2. 기존 5건 불일치 — 수정 완료 ✅

| # | 심각도 | 항목 | 문제 | 수정 내용 | 확인 위치 |
|---|--------|------|------|-----------|-----------|
| 1 | CRITICAL | 섹션 ID | Title Case 13개 → 백엔드 snake_case 21개 불일치 | `SectionId` 유니온 타입 21개, `STRUCTURAL_SECTIONS`, `CONTENT_SECTIONS`, `SECTION_LABEL_MAP` 추가 | `types/document.ts:24-97` |
| 2 | CRITICAL | Company fetch_status | "COLLECTING" 포함, "REFRESHING" 누락 | `CompanyFetchStatus`에서 "COLLECTING" 제거, "REFRESHING" 추가 | `types/company.ts:1` |
| 3 | MODERATE | 재생성 시 industry 누락 | handleRegenerate에 industry 미포함 | `industry: doc.industry \|\| undefined` 추가 | `DocumentDetailPage.tsx:93` |
| 4 | MODERATE | 섹션 표시 | raw snake_case ID 그대로 렌더링 | `SECTION_LABEL_MAP[section]`으로 라벨 변환 | `DocumentDetailPage.tsx:245-258`, `CreateDocumentPage.tsx:386-400` |
| 5 | LOW | Mock 데이터 | 유효하지 않은 섹션 ID, industry 누락 | snake_case ID로 교체, `industry` 필드 추가 | `mocks/data.ts:209`, `mocks/handlers.ts:134` |

---

## 3. 1차 점검에서 추가 발견 + 수정 — 2건 ✅

| # | 심각도 | 항목 | 문제 | 수정 내용 | 확인 위치 |
|---|--------|------|------|-----------|-----------|
| 6 | LOW | DocumentListResponse 타입 불완전 | 백엔드가 `offset`, `limit`도 반환하지만 FE 타입에 누락 | 응답 타입에 `offset: number; limit: number` 추가 | `useDocuments.ts:19` |
| 7 | LOW | DocumentListParams에 `search` 누락 | 백엔드가 `search` 쿼리 파라미터 지원하지만 FE 미정의 | `search?: string` 추가 | `types/document.ts:132` |

---

## 4. 2차 종합 점검 — 추가 불일치 없음 ✅

### 4-1. 타입/스키마 필드별 대조

| 대상 | 필드 수 | 결과 |
|------|---------|------|
| `Document` ↔ `DocumentResponse` | 18 필드 | 전부 일치 ✅ |
| `Company` ↔ `CompanyResponse` | 12 필드 | 전부 일치 ✅ |
| `DocumentCreate` (FE ↔ BE) | 7 필드 | 전부 일치 ✅ |

### 4-2. Enum/Union 값 대조

| 타입 | 값 수 | FE | BE | 결과 |
|------|-------|----|----|------|
| `DocumentStatus` | 7 | PENDING / COLLECTING / ANALYZING / GENERATING / RENDERING / COMPLETED / FAILED | 동일 (Python Enum) | ✅ |
| `CompanyFetchStatus` | 4 | PENDING / REFRESHING / COMPLETED / FAILED | company_service.py에서 사용 | ✅ |
| `IMStyle` | 4 | TITAN / COVENANT / FULL / CUSTOM | `_VALID_IM_STYLES` set | ✅ |
| `IndustryId` | 9 | general / tech / manufacturing / healthcare / logistics / financial_services / real_estate / energy / consumer | `_ALL_VALID_INDUSTRIES` | ✅ |
| `SectionId` | 21 | 19 기본 + 2 산업별 | `SECTION_IDS` + `INDUSTRY_SECTION_IDS` | ✅ |

### 4-3. API 엔드포인트 대조

| FE 훅 | 메서드 | 경로 | BE 라우트 | 상태코드 | 결과 |
|--------|--------|------|-----------|----------|------|
| `useDocuments` | GET | /documents | `list_documents` | 200 | ✅ |
| `useDocument` | GET | /documents/{id} | `get_document` | 200 | ✅ |
| `useCreateDocument` | POST | /documents | `create_document` | 202 | ✅ |
| `useDownloadDocument` | GET | /documents/{id}/download?format= | `download_document` | 200 | ✅ |
| `useCompany` | GET | /companies/{corpCode} | `get_company_data` | 200 | ✅ |
| `useFetchCompany` | POST | /companies | `fetch_company_data` | 202 | ✅ |

Vite 프록시: `/api/im` → `localhost:8002/api/v1` ✅

### 4-4. 클라이언트 사이드 Validation 대조

| 항목 | 백엔드 검증 | 프론트엔드 검증 | 결과 |
|------|-------------|-----------------|------|
| corp_code 8자리 | `min_length=8, max_length=8, isdigit()` | `corpCodeInput.length !== 8` 체크 | ✅ |
| pdf_password 최소 4자 | `min_length=4` | `length > 0 && length < 4` 에러 표시 + 제출 비활성화 | ✅ |
| im_style 유효값 | `_VALID_IM_STYLES` set | `IMStyle` 유니온 타입 | ✅ |
| industry 유효값 | `_ALL_VALID_INDUSTRIES` set | `IndustryId` 유니온 타입 | ✅ |

### 4-5. 데이터 흐름 확인

| 흐름 | 상태 |
|------|------|
| CUSTOM 섹션 합산: `STRUCTURAL_SECTIONS + formData.sections` → 중복 제거 후 전송 | ✅ |
| Industry 자동 매핑: DART 산업명 → IndustryId (9개 전부 커버) | ✅ |
| 문서 폴링: IN_PROGRESS 상태 시 3초 간격 | ✅ |
| 기업 폴링: PENDING/REFRESHING 시 3초 간격 | ✅ |
| 다운로드: blob + content-disposition filename 추출 | ✅ |
| 페이지네이션: offset/limit + total 계산 | ✅ |

---

## 5. 수정 불필요 사항 (참고)

| 항목 | 사유 |
|------|------|
| BE `generation_config`, `stage_details` JSONB 미노출 | 의도적 설계 — 서버 내부 파이프라인 데이터 |
| BE Company `dart_data`, `financial_summary`, `brand_assets` 미노출 | 서버 사이드 전용 캐시 데이터 |
| Celery 태스크가 DB fetch_status 직접 미갱신 | 알려진 BE 아키텍처 이슈, 별도 대응 필요 |
| `webhook_url` UI 미노출 | 현재 UI에 불필요 (API 전용 기능) |
| UUID 직렬화 (BE UUID → JSON string → FE string) | 런타임 정상 동작 |
| DateTime 직렬화 (BE datetime → ISO-8601 string → FE string) | 런타임 정상 동작 |

---

## 6. 수정 파일 목록 (총 9개)

| 위치 | 파일 | 변경 내용 |
|------|------|-----------|
| FE Types | `src/modules/im/types/document.ts` | `SectionId` 유니온, `CONTENT_SECTIONS`, `STRUCTURAL_SECTIONS`, `SECTION_LABEL_MAP`, `Document.industry`, `DocumentListParams.search` |
| FE Types | `src/modules/im/types/company.ts` | `CompanyFetchStatus`: COLLECTING → REFRESHING |
| FE Hooks | `src/modules/im/hooks/useCompanies.ts` | 폴링 조건 `["PENDING", "REFRESHING"]` |
| FE Hooks | `src/modules/im/hooks/useDocuments.ts` | 응답 타입에 `offset`, `limit` 추가 |
| FE Pages | `src/modules/im/pages/CreateDocumentPage.tsx` | 섹션 UI 전체 교체 (CONTENT_SECTIONS import), industry 전송, STRUCTURAL_SECTIONS 합산 |
| FE Pages | `src/modules/im/pages/DocumentDetailPage.tsx` | `SECTION_LABEL_MAP` 라벨 표시, `handleRegenerate`에 industry 추가 |
| FE Tests | `src/test/mocks/data.ts` | 섹션 ID → snake_case, `industry` 필드 추가 |
| FE Tests | `src/test/mocks/handlers.ts` | POST /documents 응답에 `industry: "general"` 추가 |
| BE Model | `IM Module/.../db/models/document.py` | `@property industry` 추가 |
| BE Schema | `IM Module/.../schemas/documents.py` | `DocumentResponse.industry: str \| None` 추가 |

---

## 7. 결론

**IM 모듈 프론트엔드-백엔드 간 불일치가 모두 해소되었다.**

- 기존 5건 (CRITICAL 2 + MODERATE 2 + LOW 1): 수정 완료
- 추가 2건 (LOW 2): 수정 완료
- 2차 종합 점검: 추가 불일치 없음 확인
