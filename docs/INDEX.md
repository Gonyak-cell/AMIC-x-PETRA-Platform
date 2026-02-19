# AMIC x PETRA Platform — 문서 색인

> 최종 업데이트: 2026-02-19 00:46

## 폴더 구조

| 카테고리 | 폴더 | 설명 | 문서 수 |
|---------|------|------|--------|
| 아키텍처 | `architecture/` | 전체 프로젝트 구조, 통합 계획, 포털 설계, M&A 워크플로우 | 9 |
| 코드 리뷰 | `code-review/` | 코드 리뷰 리포트, 프롬프트, 프로토콜 | 22 |
| 보안 | `security/` | 보안 감사, JWT/인증 마이그레이션 | 2 |
| 배포 | `deployment/` | 배포 체크리스트, 빌드 리포트, 개발환경 포트 | 3 |
| FDD 모듈 | `fdd/` | FDD 백엔드 워크플로, 템플릿, LLM 프롬프트 | 3 |
| KIIS 모듈 | `kiis/` | KIIS 구현 계획, 워크플로, 펀드 상세, 캐싱, GP 전환 | 7 |
| IM 모듈 | `im/` | IM 워크플로, 템플릿, 시각화 | 4 |
| 프론트엔드 | `frontend/` | UI 리프레시, 통합 프론트엔드 계획, MSW | 3 |
| 테스트 | `testing/` | E2E 테스트 계획 | 1 |

---

## architecture/ — 아키텍처 및 통합 계획 (7)

| 파일명 | 설명 |
|--------|------|
| `AMIC_최종_통합계획서_Final.md` | AMIC x PETRA 최종 통합 계획서 |
| `AMIC_전체_프로젝트_구조.md` | 전체 프로젝트 구조 개요 |
| `통합_플랫폼_구현_계획서.md` | 통합 플랫폼 구현 상세 계획 |
| `Full_Integration_Plan.md` | 전체 통합 계획 (영문) |
| `Portal_Enhancement_Plan.md` | 포털 UX 개선 Wave별 계획 |
| `claude-config-gap-fill-plan.md` | Claude Code 설정 갭 분석 및 표준화 |
| `20260219_0046_MA_Workflow_Implementation_Plan.md` | 7단계 M&A 워크플로우 상세 구현 계획 (deal-mgmt 서비스, Phase 0~2 완료) |
| `20260218_2124_MA_Phase0_Implementation_Tickets.md` | MA Phase 0 구현 티켓 상세 (스캐폴딩, Docker, 프록시) |
| `20260218_0005_MA_Branch_Strategy.md` | MA 워크플로우 브랜치 전략 (백업 태그, 작업 브랜치 가이드) |

## code-review/ — 코드 리뷰 (22)

| 파일명 | 설명 |
|--------|------|
| `20260213_0833_FDD_Code_Review.md` | FDD 모듈 코드 리뷰 (Session 1) |
| `20260213_0836_KIIS_Code_Review.md` | KIIS 모듈 코드 리뷰 (Session 1) |
| `20260213_0906_Code_Review_Prompts.md` | 코드 리뷰 프롬프트 V1 |
| `20260213_0926_KIIS_Code_Review_Session3.md` | KIIS 코드 리뷰 (Session 3) |
| `20260213_0927_FDD_Code_Review_Session2.md` | FDD 코드 리뷰 (Session 2) |
| `20260213_0957_Platform_Code_Review.md` | 플랫폼 공통 코드 리뷰 |
| `20260213_1003_IM_Module_Code_Review.md` | IM 모듈 코드 리뷰 |
| `20260213_1222_Platform_Code_Review_Supplement.md` | 플랫폼 코드 리뷰 보충 |
| `20260213_1228_FDD_Code_Review_Session3.md` | FDD 코드 리뷰 (Session 3) |
| `20260213_1231_Code_Review_Prompts_V2.md` | 코드 리뷰 프롬프트 V2 |
| `20260213_1253_Verified_Code_Review.md` | Verified Claim Protocol 기반 리뷰 |
| `20260213_1344_Code_Review_Prompts_V3.md` | 코드 리뷰 프롬프트 V3 |
| `20260213_1413_IM_Backend_Pipeline_Code_Review.md` | IM 백엔드 파이프라인 리뷰 |
| `20260213_1455_Phase1_Code_Review_Report.md` | Phase 1 코드 리뷰 리포트 |
| `20260213_1516_Phase2_Code_Review_Report.md` | Phase 2 코드 리뷰 리포트 |
| `20260213_1544_Phase3_Code_Review_Report.md` | Phase 3 코드 리뷰 리포트 |
| `20260213_1815_Phase4_Code_Review_Report.md` | Phase 4 코드 리뷰 리포트 |
| `20260216_1907_Code_Review_Architecture_Redesign.md` | 코드 리뷰 시스템 아키텍처 재설계 |
| `20260216_1949_Code_Review_Execution_Plan.md` | 코드 리뷰 실행 계획 |
| `20260216_2010_App_Quick_Code_Review.md` | App 빠른 코드 리뷰 |
| `20260216_2028_KIIS_Module_Code_Review.md` | KIIS 모듈 코드 리뷰 (최신) |
| `20260216_2055_Full_Code_Review.md` | 전체 프론트엔드 코드 리뷰 (최종) |

## security/ — 보안 (2)

| 파일명 | 설명 |
|--------|------|
| `20260216_2022_Security_Code_Review.md` | 보안 코드 리뷰 |
| `20260216_2152_JWT_HTTPOnly_Cookie_Migration_Plan.md` | JWT → httpOnly 쿠키 마이그레이션 계획 |

## deployment/ — 배포 (2)

| 파일명 | 설명 |
|--------|------|
| `20260213_1859_Deployment_Checklist.md` | 배포 전 체크리스트 |
| `20260217_0027_Session22_Build_Deploy_Report.md` | Session 22 빌드/배포 리포트 |
| `20260217_1907_Dev_Port_5173_vs_3000.md` | 개발환경 포트 가이드 (5173 vs 3000 로그인 이슈) |

## fdd/ — FDD 모듈 (3)

| 파일명 | 설명 |
|--------|------|
| `20260217_0234_FDD_Workflow_Analysis.md` | FDD 워크플로 분석 |
| `20260217_1339_FDD_Template_SlotFill_System_Plan.md` | FDD 템플릿 Slot-Fill 시스템 계획 |
| `20260217_0159_MultiLLM_Industry_Prompt_Improvement_Plan.md` | 멀티LLM 산업별 프롬프트 개선 (FDD+IM) |

## kiis/ — KIIS 모듈 (4)

| 파일명 | 설명 |
|--------|------|
| `Phase2_KIIS_Implementation_Plan.md` | KIIS Phase 2 구현 계획 |
| `20260217_0238_KIIS_Workflow_Analysis_Plan.md` | KIIS 워크플로 분석 계획 |
| `20260217_1152_KIIS_FundDetailPage_Enhancement_Plan.md` | KIIS 펀드 상세 페이지 개선 계획 |
| `20260217_1810_KIIS_Fund_Search_API_Research.md` | KIIS 펀드 검색 API 리서치 |
| `20260217_1852_KOFIA_Caching_System.md` | KOFIA 3계층 캐싱 시스템 구현 |
| `20260217_1904_KIIS_Qualitative_Reputation_Tendency_Implementation.md` | 정성적 평판·투자성향 분석 구현 보고서 |
| `20260217_2136_GP_Centric_Search_Implementation.md` | GP(운용사) 중심 검색 전환 구현 보고서 |

## im/ — IM 모듈 (4)

| 파일명 | 설명 |
|--------|------|
| `20260212_1659_IM_FE_BE_Mismatch_Audit.md` | IM 프론트/백엔드 불일치 감사 |
| `20260217_0234_IM_Workflow_Analysis.md` | IM 워크플로 분석 |
| `20260217_1316_IM_Template_SlotFill_System_Plan.md` | IM 템플릿 Slot-Fill 시스템 계획 |
| `20260217_1340_IM_Visualization_Auto_Generation.md` | IM 시각화 자동 생성 계획 |

## frontend/ — 프론트엔드 (3)

| 파일명 | 설명 |
|--------|------|
| `통합_프론트엔드_구현_계획.md` | 통합 프론트엔드 구현 계획 |
| `UI_Refresh_Plan.md` | UI 리프레시 (dealroom.net 스타일) 계획 |
| `20260217_1607_MSW_Auth_Handler_Fix.md` | MSW 인증 핸들러 수정 |

## testing/ — 테스트 (1)

| 파일명 | 설명 |
|--------|------|
| `Browser_E2E_Deep_Test_Plan.md` | 브라우저 E2E 딥 테스트 계획 |

---

## 문서 분류 기준

새 문서 작성 시 아래 기준에 따라 적절한 폴더에 저장:

| 카테고리 | 저장 폴더 | 키워드 |
|---------|----------|--------|
| 전체 아키텍처/통합 계획 | `architecture/` | 통합, 구조, 포털, 설정, 전체 |
| 코드 리뷰/감사 | `code-review/` | Code Review, 리뷰, 리포트, 프롬프트 |
| 보안/인증 | `security/` | Security, JWT, 인증, XSS, CORS |
| 배포/인프라 | `deployment/` | Deploy, 배포, 빌드, CI/CD, Docker |
| FDD 모듈 전용 | `fdd/` | FDD, 실사, Due Diligence |
| KIIS 모듈 전용 | `kiis/` | KIIS, 펀드, REIT, 공시 |
| IM 모듈 전용 | `im/` | IM, 투자설명서, Information Memorandum |
| 프론트엔드 공통 | `frontend/` | UI, UX, 컴포넌트, MSW, 프론트엔드 |
| 테스트 | `testing/` | E2E, 테스트, Playwright, Vitest |
