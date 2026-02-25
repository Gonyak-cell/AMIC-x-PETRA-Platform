# Docs + MA 모듈 전체 코드 리뷰 리포트
> 작성: 2026-02-23 12:14:58
> VCP(Verified Claim Protocol) v1.1 준수
> 브랜치: `feat/ma-workflow`

---

## Executive Summary

| 구분 | 건수 |
|------|------|
| 리뷰 파일 수 | 48개 (docs 15 + ma 33) |
| 발견 이슈 (수정 전) | 22건 |
| 허위양성 REJECT | 2건 |
| 최종 확인 이슈 | 20건 |
| **이번 세션 수정 완료** | **12건** |
| 이월 (아키텍처 범위) | 8건 |

---

## 수정 완료 이슈 (12건)

### Docs 모듈

| ID | 파일 | 라인 | 심각도 | 내용 | 상태 |
|----|------|------|--------|------|------|
| D-001 | `CreateDocumentPage.tsx` | 127 | Moderate | URL 파라미터 타입 단언 → 타입 가드로 교체 | ✅ 수정 |
| D-003 | `useFDDDocuments.ts` | 30 | Moderate | `industry as Deal["industry"]` → `isIndustryId()` 가드 | ✅ 수정 |
| D-004 | `useFDDDocuments.ts` | 44-47 | Major | Orphan Deal — Version 생성 실패 시 에러 추적 메시지 | ✅ 수정 |
| D-005 | `PPTStylePicker.tsx` | 226-237 | Minor | label `htmlFor` + input `id` 연결 (접근성 WCAG 2.1) | ✅ 수정 |
| D-006 | `CreateDocumentPage.tsx` | 398-401 | Minor | FDD 에러 시 toast.error 누락 수정 | ✅ 수정 |

### MA 모듈 — 훅 성공 토스트 일관성

| ID | 파일 | 라인 | 심각도 | 내용 | 상태 |
|----|------|------|--------|------|------|
| m-R002 | `useTransactions.ts` | 303-307 | Moderate | `useUpdateBuyer` onSuccess 토스트 추가 | ✅ 수정 |
| m-R003 | `useRisks.ts` | 91-95 | Moderate | `useUpdateRisk` onSuccess 토스트 추가 | ✅ 수정 |
| m-R004 | `useCompliance.ts` | 89-93 | Moderate | `useUpdateCompliance` onSuccess 토스트 추가 | ✅ 수정 |
| DD-fix | `useDDChecklist.ts` | 89-93 | Moderate | `useUpdateDDChecklistItem` onSuccess 토스트 추가 | ✅ 수정 |

### MA 모듈 — 페이지

| ID | 파일 | 라인 | 심각도 | 내용 | 상태 |
|----|------|------|--------|------|------|
| ISSUE-005 | `TransactionWorkspacePage.tsx` | 2454 | Moderate | `key={i}` → `key={a.email}` 안정적 key | ✅ 수정 |
| ISSUE-008 | `CreateTransactionPage.tsx` | 131 | Minor | 토글 버튼 `aria-expanded` 추가 | ✅ 수정 |
| ISSUE-009 | `TransactionWorkspacePage.tsx` | 2854 | Minor | NDA 모달 취소 시 폼 상태 초기화 | ✅ 수정 |

---

## 허위양성 REJECT (2건)

| ID | 이슈 | 거부 사유 |
|----|------|---------|
| D-002 | PPTStylePicker XSS 위험 | React JSX 텍스트 인터폴레이션 자동 HTML-escape. `dangerouslySetInnerHTML` 미사용 → 안전함 |
| test-fix | DashboardPage "New IM" | `DashboardPage.tsx` 퀵액션 레이블이 "New Document"로 변경됨 — 테스트 업데이트로 수정 |

---

## 이월 이슈 (아키텍처 범위)

> 현재 세션에서 수정 범위를 초과하는 이슈. 별도 스프린트 계획 권장.

| ID | 파일 | 심각도 | 내용 | 권장 시점 |
|----|------|--------|------|---------|
| M-T001 | `ma/types/contract.ts:82` | Major | `AIRiskFlag.risk_level: string` → 유니온 타입 | 백엔드 스키마 확인 후 |
| L-T001 | `ma/types/bid.ts:63` | Minor | `BidComparisonItem.buyer_type: string` → `BuyerType` | 백엔드 확인 후 |
| m-R001 | `ma/hooks/useApprovals.ts:14` | Moderate | queryKey 객체 포함 → primitive 분해 | 성능 최적화 스프린트 |
| D-007 | `CreateDocumentPage.tsx:319` | Minor | industry 검증 일관성 (FDD Step 이동) | 문서 생성 리팩토링 시 |
| ISSUE-001 | `TransactionWorkspacePage.tsx` | Major | 43개 훅 → 탭별 선택적 로드 | Phase 4 성능 스프린트 |
| ISSUE-003 | `TransactionWorkspacePage.tsx` | Moderate | 단일 승인자 가정 → 다중 승인 지원 | MA Phase 3 |
| ISSUE-004 | `TransactionWorkspacePage.tsx` | Moderate | 3,400라인 단일 컴포넌트 분할 | Phase 4 리팩토링 |
| ISSUE-006 | `TransactionWorkspacePage.tsx` | Moderate | 필터 버튼 ARIA (`role="group"`, `aria-pressed`) | 접근성 스프린트 |

---

## 모달 폼 초기화 — 패턴 경고

`TransactionWorkspacePage.tsx` 내 모든 모달의 Cancel 버튼이 폼 상태를 초기화하지 않는 패턴이 5개 이상 있다.
이번 세션에서는 NDA 모달(ISSUE-009)만 수정했다. 나머지 모달들도 동일 수정 필요:

| 모달 | Cancel 라인 | 초기화 대상 |
|------|------------|------------|
| Engagement 모달 | ~2612 | `setEngForm({ type: "EXCLUSIVE" })` |
| Member 모달 | ~2697 | `setMemberForm({ name: "", email: "", role: "LEAD_ADVISOR" })` |
| Buyer 모달 | ~2783 | `setBuyerForm({ company_name: "", buyer_type: "STRATEGIC" })` |
| Bid 모달 | ~2956 | `setBidForm(...)` |
| DD 모달 | ~3033 | `setDDForm(...)` |

---

## 프로덕션 배포 준비 상태

### 코드 측 (이번 세션 완료)
- ✅ TypeScript tsc --noEmit 오류 0건
- ✅ ESLint max-warnings 0 통과
- ✅ Vitest 98/98 테스트 통과 (DashboardPage 테스트 수정 포함)
- ✅ Vite 프로덕션 빌드 성공

### 외부 의존성 체크리스트 (사용자 조치 필요)

| 순서 | 항목 | 예상 소요 |
|------|------|---------|
| 1 | **Sentry 계정 생성** + 프로젝트 생성 | 25분 |
| 2 | **GitHub Secrets 등록** (`scripts/setup-github-secrets.ps1`) | 20분 |
| 3 | **LLM API 키** (OpenAI/Anthropic/Google 중 최소 1개) | 30분 |
| 4 | **DART API 키** (opendart.fss.or.kr) | 1시간 |
| 5 | **프로덕션 서버** (Ubuntu 24.04, 24GB RAM, 100GB SSD) | 30분 |
| 6 | **도메인 + DNS + SSL** | 2~24시간 |

### 서버 배포 명령 (외부 의존성 충족 후)

```bash
# 1. 클론 + 환경 설정
git clone https://github.com/{org}/AMIC-x-PETRA-Platform.git /opt/amic
cd /opt/amic && git checkout master
cp .env.production.example .env  # 모든 CHANGE_ME 항목 채우기

# 2. 빌드 + 실행
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 3. DB 마이그레이션
docker compose exec fdd-api alembic upgrade head
docker compose exec kiis-api alembic upgrade head
docker compose exec im-api alembic upgrade head
docker compose exec deal-mgmt-api alembic upgrade head

# 4. 헬스체크
curl http://localhost/api/fdd/health && \
curl http://localhost/api/kiis/health && \
curl http://localhost/api/im/health && \
curl http://localhost/api/ma/health
```

---

## 배포 준비도 평가 (2026-02-23 기준)

| 영역 | 준비도 |
|------|--------|
| 프론트엔드 코드 | ✅ 95% |
| MA + Docs 모듈 코드 | ✅ 95% (이슈 수정 후) |
| Docker 인프라 | ✅ 92% |
| nginx 보안 헤더 | ✅ 95% |
| 환경변수 템플릿 | ✅ 88% |
| CI/CD 파이프라인 | ✅ 90% |
| 외부 의존성 (Sentry, API 키) | ⏳ 사용자 조치 필요 |
| 서버/도메인/SSL | ⏳ 사용자 조치 필요 |
| **종합** | **75~80%** |
