# Review Index

> 최종 업데이트: 2026-02-25 21:55:00

## 카테고리별 요약

| 카테고리 | 총 건수 | 최근 문서 |
|---------|--------|----------|
| bugfix | 13건 | 20260225_2155_IM_Design_Visualization_Code_Review_Fixes.md |
| security | 1건 | 20260217_1716_Cookie_Auth_Cross_Backend.md |
| review | 7건 | 20260225_2131_FDD_MultiLLM_CrossVerification_Review_and_Fix.md |
| refactor | 1건 | 20260224_1252_Backend_Code_Quality_Refactoring.md |
| a11y | 1건 | 20260223_1216_PPTStylePicker_label_aria.md |
| perf | 0건 | — |
| hotfix | 0건 | — |
| type | 1건 | 20260223_1215_FDD_industry_type_assertion.md |
| build | 0건 | — |
| ui | 8건 | 20260225_1246_MA_Sidebar_Workflow_Restructure_Review.md |

## 전체 내역 (최신순)

| 날짜 | 카테고리 | 요약 | 심각도 | 파일 |
|------|---------|------|--------|------|
| 2026-02-25 | bugfix | **IM 디자인/시각화 코드 리뷰 수정 18건** — P0: `_parse_number()` 한국 통화 단위 승수 적용, P1: chart 중복 제거/브랜드 파생 필드/set_font_with_ea 5곳/Celery time_limit/pipeline success 판정, P2: 시맨틱 컬러/NanumGothic→NotoSansKR/폴백 에러 마스킹/combo 검증/a11y/UniqueConstraint, P3: docstring/좌표/private→public/badge 중복 — tsc + vite build ✅ | P0~P3 | `bugfix/20260225_2155_IM_Design_Visualization_Code_Review_Fixes.md` |
| 2026-02-25 | review | **FDD 멀티 LLM 교차검증 코드 리뷰 및 수정** — 10건 이슈(C:2 M:4 Mo:3 m:1) 전체 수정 완료: AnalysisRun import/dead code/로깅(P0), NWC/Debt 변환/break 제거/reviewer_only 처리/source_data 채우기(P1), FE 타입/confidence/규칙3(P2), 10/10 테스트 통과 — **✅ 전체 수정 완료** | Critical~Minor | `review/20260225_2131_FDD_MultiLLM_CrossVerification_Review_and_Fix.md` |
| 2026-02-25 | bugfix | **Financial Models GET 500 에러 — Alembic 마이그레이션 체인 수정** — Migration 019 asyncpg multi-statement 분리, 020 enum 중복 CREATE TYPE 제거, 021 down_revision 체인 불일치 수정. DB 018→021_rfi 완료, 7개 테이블 생성, API 200 OK — **✅ 수정 완료** | Critical | `bugfix/20260225_2125_Financial_Models_500_Migration_Chain_Fix.md` |
| 2026-02-25 | review | **Financial Model 코드 리뷰 및 수정** — 18건 이슈(C:3 M:5 Mo:6 m:4), 13건 수정 완료, JWT 인증 6개 추가/경로 순회 방지/Celery 멱등성 가드/finalize 원자성/regenerate 상태 가드+트리거/WACC Kd 명칭/Input 카테고리 필터링/NOT_APPLICABLE 집계, 20/20 테스트 통과 — **✅ 수정 완료** | Critical~Moderate | `review/20260225_2104_Financial_Model_Code_Review_and_Fix.md` |
| 2026-02-25 | review | **FDD 전체 리뷰 통합** — 8건 리뷰 이력(2/17~2/25) 통합, 총 32건 이슈(수정 29 + 허위양성 3), 보안 수정 3건(IDOR/권한/enum), 테스트 1439 passed — **✅ 통합 문서 작성 완료** | — | `review/20260225_2054_FDD_Full_Review_Summary.md` |
| 2026-02-25 | bugfix | FDD 테스트 스위트 70건 실패 수정 — Phase 1: `target_company_name` 필수 필드 누락 6곳(63건), Phase 2: httpOnly 쿠키 전환/bcrypt 전환/VIEWER 권한 확장/페이지네이션 형식 등 7건 — **✅ 1439 passed, 0 failed** | Medium (P2) | `bugfix/20260225_1823_FDD_Test_Suite_70_Failures_Fix.md` |
| 2026-02-25 | review | FDD Ralph Loop 2-Pass 전체 코드 리뷰 — BUG-1 Refined IR 렌더러 미적용 수정(`_patch_report_ir`), BUG-2 테스트 픽스처 `body`→`content` 수정, 13개 영역 정합성 검증 완료 — **✅ 3건 수정 완료** | Critical+Medium (P0+P2) | `review/20260225_1750_FDD_Ralph_Loop_Code_Review.md` |
| 2026-02-25 | ui | MA 사이드바 워크플로우 재구성 — 7단계 워크플로우 섹션 + Tools 섹션 추가, phase 상태별 시각적 표시(done/current/future), BUG-001 `h-4.5` 무효 Tailwind 클래스 수정 — **✅ 완료** | UI (P2) | `ui/20260225_1246_MA_Sidebar_Workflow_Restructure_Review.md` |
| 2026-02-25 | bugfix | IM Documents 500 에러 — users.title 마이그레이션 미적용 수정 + docker-compose.yml 4개 백엔드 자동 마이그레이션 추가 — **✅ 완료** | Critical | `bugfix/20260225_1058_IM_Documents_500_User_Title_Migration.md` |
| 2026-02-25 | bugfix | AUTH_ENABLED=false dev 사용자 덮어쓰기 수정 — docker-compose.yml 4개 백엔드 AUTH_ENABLED "false"→"true" 전환, JWT 검증 활성화 — **✅ 완료** | Critical | `bugfix/20260225_0943_AUTH_ENABLED_Dev_User_Override_Fix.md` |
| 2026-02-24 | ui | 디자인 토큰 시스템 롤백 + 미정의 토큰 6종 수정 — CSS 변수 기반 시스템 도입 후 시각 품질 하락으로 전체 롤백(~350건), 실제 미정의 토큰만 hex로 추가 해결 — **✅ 완료** | UI (P2) | `ui/20260224_2224_Design_Token_System_Revert_and_Fix.md` |
| 2026-02-24 | ui | MA 파이프라인 이전 단계 탭 네비게이션 — viewedPhase state 기반 단계 전환, navigate 레이스 컨디션 해소, safeActiveTab 렌더 시점 계산, 조건부 렌더링 18곳 교체 — **✅ 완료** | UX (P2) | `ui/20260224_2148_MA_Pipeline_Phase_Navigation.md` |
| 2026-02-24 | review | MA 워크플로우 전제 조건 2-Tier 분리 + 자동 전환 알림 — REQUIRED/RECOMMENDED 분리, 조건 완화 3건, useAutoAdvanceNotification 훅, PhaseActionPanel 2-tier UI, 코드 리뷰 W-1/W-2 수정 — **✅ 완료** | Medium (P2) | `review/20260224_2024_MA_Workflow_Two_Tier_Prerequisites.md` |
| 2026-02-24 | ui | MOU 파이프라인 독립 그룹 이동 — 서비스 연동 사이드바에서 마케팅↔DD 사이에 MOU 그룹 추가, 계약/협상 법률문서에서 MOU 제거, 타입 피커에서 MOU 제거 — **✅ 완료** | UI (P3) | `ui/20260224_1621_MOU_Pipeline_Independent_Group.md` |
| 2026-02-24 | ui | FDD → DD/Checklist 탭 연동 — "COMING SOON" 제거, FDDReportsTab 컴포넌트 신규 생성, 기존 FDD 보고서 훅 재사용 — **✅ 완료** | UI (P3) | `ui/20260224_1539_FDD_DD_Report_Integration.md` |
| 2026-02-24 | refactor | 백엔드 코드 품질 리팩토링 — P1 3건(JWT 가드, RFC 7807 통일, N+1 쿼리) + P2 2건(CORS 명시, 페이지네이션 헬퍼) 총 17파일 수정 — **✅ 완료** | P1~P2 | `refactor/20260224_1252_Backend_Code_Quality_Refactoring.md` |
| 2026-02-24 | bugfix | 프론트-백엔드 전체 연동 검증 — 67개 훅 교차 검증, BUG 7건 발견 (5건 수정: useAnalytics 응답 파싱, change-password 엔드포인트, 글로벌 검색, KIIS 경로 불일치, tendency-summary 엔드포인트) — **✅ 수정 완료** | P0~P3 | `bugfix/20260224_0125_Frontend_Backend_Integration_Review.md` |
| 2026-02-23 | bugfix | 마케팅 자료(TM/DM/IM) 버그 수정 (5건): DB 세션 생명주기 버그(asyncio.create_task), python-pptx 의존성 누락, 테스트 픽스처 미정의, 삭제 확인 대화 부재, 한글 파일명 새니타이제이션 — **✅ 수정 완료** | Critical×3+Major+Medium | `bugfix/20260223_1653_Marketing_Materials_Bug_Fixes.md` |
| 2026-02-23 | bugfix | Deal Document Studio 신규 버그 수정 (2건): 다운로드 URL `/api/v1` → `/api/ma` proxy 경로 수정, txnId 없을 때 생성 버튼 disabled 처리 — **✅ 수정 완료** | Critical+Minor | `bugfix/20260223_1444_Deal_Document_Studio_New_Bugs.md` |
| 2026-02-23 | bugfix | Deal Document Studio 전체 리뷰 수정 (15건): 경로 탐색 방어, 소유권 검증, 템플릿 검증, Pydantic 날짜/범위 검증, a11y radiogroup+label, LegalParamsForm 타입 강화, 에러 상세화, GENERATING 폴링, 커스텀 예외 분리, DB 인덱스, 추가 테스트 7건, 파일 정리 스크립트 — **✅ 수정 완료** | P0~P2 (Critical~Minor) | `bugfix/20260223_1339_Deal_Document_Studio_Review_Fixes.md` |
| 2026-02-23 | a11y | PPTStylePicker label/input 연결 + CreateTransactionPage aria-expanded 추가 — WCAG 2.1 준수 — **✅ 수정 완료** | Minor (P3) | `a11y/20260223_1216_PPTStylePicker_label_aria.md` |
| 2026-02-23 | type | FDD industry 타입 단언 → isIndustryId() 타입 가드 교체 — **✅ 수정 완료** | Moderate (P2) | `type/20260223_1215_FDD_industry_type_assertion.md` |
| 2026-02-23 | bugfix | Docs + MA 전체 리뷰 수정 (12건): URL 타입 가드, FDD 에러 메시지, Orphan Deal 추적, MA 훅 토스트 4건, NDA 모달 초기화, key={i}, DashboardPage 테스트 — **✅ 수정 완료** | Major~Minor | `bugfix/20260223_1215_Docs_MA_Review_Fixes.md` |
| 2026-02-23 | review | GSAP 모션 시스템 코드 리뷰 — P0 timeScale(0) 접근성 버그, P1 GPListPage 조건부 ref, P2 useCountUp 데드 코드 + 허위 양성 12건 필터링 — **✅ 3건 수정 완료** | Critical+High (P0+P1+P2) | `review/20260223_0934_GSAP_Motion_System_Code_Review.md` |
| 2026-02-22 | ui | InlineSelect 컴포넌트 + 인라인 편집 확장 — native select 7곳 교체, 인라인 편집 7개 필드 추가, 빌드 에러 수정 — **✅ 완료** | Moderate (P2) | `ui/20260222_0144_InlineSelect_InlineEdit_Expansion.md` |
| 2026-02-17 | ui | FDD 딜 생성 폼 리디자인 — 필수/선택 분리, 접이식 추가 정보, "선택 안함" 기본값, Docker HMR 수정 — **✅ 완료** | Moderate (P2) | `ui/20260217_2153_FDD_Deal_Form_Redesign.md` |
| 2026-02-17 | bugfix | FDD Deal 생성 500 에러 — IndustryType enum name/value 불일치 수정 + 폼 리디자인 (거래구조/투자유형/매도인유형 추가) — **✅ 수정 완료** | Critical | `bugfix/20260217_2140_FDD_Deal_Creation_500_Fix.md` |
| 2026-02-17 | ui | KIIS Companies 필터 패널 UI 개선 — FundFilterPanel 패턴 적용, 다중 시장 구분 Chip 필터, 검색 UX 개선 — **✅ 수정 완료** | Moderate (P2) | `ui/20260217_2102_KIIS_Company_Filter_Panel_Upgrade.md` |
| 2026-02-17 | review | KIIS 펀드 검색 핵심 3기능 점검 + 수정 (NLP 파이프라인, KOFIA 필터, 평판 자동갱신) — **✅ 전체 수정 완료** | High (P0+P1+P2) | `review/20260217_1824_KIIS_Fund_Search_Core_Feature_Audit.md` |
| 2026-02-17 | bugfix | IM 500 에러 — Redis `aclose()` 호환성 수정 — **✅ 수정 완료** | Critical | `bugfix/20260217_1748_IM_500_Redis_aclose_Fix.md` |
| 2026-02-17 | bugfix | 404 에러 — nginx health 리라이트 누락 + Cookie 전달 — **✅ 수정 완료** | Critical | `bugfix/20260217_1733_404_Error_Diagnosis_Plan.md` |
| 2026-02-17 | security | 쿠키 기반 크로스 백엔드 인증 아키텍처 수정 — **✅ 6/6 완료** | Critical (P0) | `security/20260217_1716_Cookie_Auth_Cross_Backend.md` |
