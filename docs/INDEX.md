# AMIC x PETRA Platform — 문서 색인

> 최종 업데이트: 2026-02-26 23:32:00

## 폴더 구조

| 카테고리 | 폴더 | 설명 | 문서 수 |
|---------|------|------|--------|
| 아키텍처 | `architecture/` | 전체 프로젝트 구조, 통합 계획, 포털 설계, M&A 워크플로우, Ralph Loop, VDR, 로깅/에러코드, 재무모델 | 34 |
| 코드 리뷰 | `code-review/` | 코드 리뷰 리포트, 프롬프트, 프로토콜 | 35 |
| 보안 | `security/` | 보안 감사, JWT/인증 마이그레이션 | 2 |
| 배포 | `deployment/` | 배포 체크리스트, 빌드 리포트, 개발환경 포트, 프로덕션 가이드, 에러 카탈로그 | 16 |
| FDD 모듈 | `fdd/` | FDD 백엔드 워크플로, 템플릿, LLM 프롬프트, 코드 리뷰, 감사 | 5 |
| KIIS 모듈 | `kiis/` | KIIS 구현 계획, 워크플로, 펀드 검색, 캐싱, GP 전환, 사모펀드 | 12 |
| IM 모듈 | `im/` | IM 워크플로, 템플릿, 시각화, Deal Doc Studio 통합, PPT 브랜딩, TM/DM 디자인 시스템 | 9 |
| 프론트엔드 | `frontend/` | UI 리프레시, 통합 프론트엔드 계획, MSW, GSAP 모션, 팀 페이지, 로그인/캘린더 | 8 |
| LDD 모듈 | `ldd/` | LDD 보고서 생성 프로세스 문서 | 1 |
| 테스트 | `testing/` | E2E 테스트 계획, 회귀 방지 | 2 |

---

## architecture/ (25)

| 파일명 | 설명 |
|--------|------|
| `20260210_2203_AMIC_최종_통합계획서_Final.md` | AMIC x PETRA 최종 통합 계획서 |
| `20260210_2203_AMIC_전체_프로젝트_구조.md` | 전체 프로젝트 구조 개요 |
| `20260210_2252_claude-config-gap-fill-plan.md` | Claude Code 설정 갭 분석 및 표준화 |
| `20260211_1120_통합_플랫폼_구현_계획서.md` | 통합 플랫폼 구현 상세 계획 |
| `20260211_1508_Portal_Enhancement_Plan.md` | 포털 UX 개선 Wave별 계획 |
| `20260211_2153_Full_Integration_Plan.md` | 전체 통합 계획 (영문) |
| `20260218_0006_MA_Branch_Strategy.md` | MA 워크플로우 브랜치 전략 |
| `20260218_2126_MA_Phase0_Implementation_Tickets.md` | MA Phase 0 구현 티켓 상세 |
| `20260219_0210_MA_Phase3_Phase4_Remaining_Tasks.md` | MA Phase 3~4 잔여 작업 목록 |
| `20260220_1413_MA_Workflow_Implementation_Plan.md` | MA 워크플로우 구현 계획 |
| `20260222_0133_MA_Workflow_Implementation_Plan.md` | MA 워크플로우 구현 계획 (최신) |
| `20260222_0140_MA_Phase5B_Docker_E2E_Completion.md` | MA Phase 5B 완료 및 Docker E2E 검증 보고서 |
| `20260222_1635_Session31_Progress_Check_Report.md` | Session 31 진행상황 점검 보고서 (E2E, SEC-001, UI Refresh, 사모펀드) |
| `20260222_2211_Session33_Work_Report.md` | Session 33 작업 보고서 (리포 동기화, GSAP 검증, 사모펀드 GP Phase 1, 배포 점검) |
| `20260223_0027_MA_Phase3_Detailed_Plan.md` | MA Phase 3 상세 기획서 (AI 계약분석, DocuSign 전자서명, Closing 자동화) |
| `20260223_1211_Project_Rules_Master.md` | **프로젝트 전체 적용 규칙 총람** (도구 자율성, Git, 문서, 리뷰, VCP, 모듈별 규칙) |
| `20260223_1222_Tofu_AT_Adoption_Analysis.md` | Tofu-AT 도입 장단점 분석 (기존 인프라 대비 득실, 최소 설치 권고) |
| `20260223_1318_Legal_Documents_Feature_Implementation.md` | 법률 문서 생성 기능 구현 보고서 (SPA/SHA/BTA/SSA/MOU, deal-mgmt + Docs Studio 통합) |
| `20260223_1511_Full_System_Feature_Structure.md` | **전체 시스템 기능 구조 분석** — 5개 프론트엔드 모듈, 4개 백엔드 서비스, 인프라, 서비스 간 연동 흐름 |
| `20260223_1637_Marketing_Materials_TM_DM_IM_Implementation.md` | MA 워크플로우 마케팅 자료(TM/DM/IM) PPTX 생성 기능 구현 보고서 — memo_generator.py 통합, 배포 추적, Forest 테마 디자인 시스템 |
| `20260223_2206_3Module_Consolidation.md` | **3모듈 체계 전환** — FDD/IM → Deal Doc Studio 통합, 최상위 모듈 4→3개 축소 (14파일 변경, 허위 양성 1건 기각) |
| `20260223_2206_ClawHub_Skills_Integration.md` | ClawHub/Claude Skills 통합 — Rules 5개 + Skills 2개 + Hooks 2개 적용, 자체 검증 리포트 포함 |
| `20260223_2252_Ralph_Loop_Phase0_Phase1_Completion.md` | Ralph Loop Phase 0~1 완료 보고서 — 코어 엔진, 파서, 생성기, 25 tests |
| `20260224_0012_Ralph_Loop_Phase2_Completion.md` | Ralph Loop Phase 2 완료 보고서 — LLM 클라이언트, Vision Gate, 학습 패턴, 79 tests |
| `20260224_0049_Ralph_Loop_Phase3_Completion.md` | Ralph Loop Phase 3 완료 보고서 — DOCXGate JSON 모드, E2E 테스트, 프론트엔드 통합, 329 tests |
| `20260224_1528_MA_DD_Tab_Consolidation_and_Workstream_Restructure.md` | MA DD 탭 통합(DD체크리스트+LDD+법률문서→2탭) 및 워크스트림 재구성(FDD 5+LDD 9+TDD 5+기타) |
| `20260224_1542_Deal_Document_Studio_Restructure.md` | Deal Document Studio 5→4 카테고리 재구성 (NDA→Legal 이동, Deal Contracts 통합, 사이드바 4섹션, 카테고리별 라우트 추가) |
| `20260224_1640_MA_Pipeline_Tab_Filtering.md` | **MA 파이프라인 단계별 탭 필터링** — 7단계별 탭 매핑, VDR 플레이스홀더, Buyers Long/Short List 서브탭, 리다이렉트 가드 |
| `20260224_2054_VDR_Module_Integration.md` | **VDR 모듈 통합** — 사이드바 독립 모듈 추가, Overview 페이지(KPI+DataTable), 404/500 디버깅(Alembic 체인 수정), 13파일 변경 |
| `20260224_2232_JSON_Structured_Logging_and_ErrorCode_Implementation.md` | **JSON 구조화 로깅 + 에러 코드 체계** — 4개 백엔드 통일 JSON 스키마, ContextVar request_id, @log_error_with_input 데코레이터, KIIS/IM/Deal-mgmt ErrorCode IntEnum(~20개/백엔드), RFC 7807 error_code 통합 |
| `20260225_0109_RotatingFileHandler_Log_File_Storage.md` | **RotatingFileHandler 로그 파일 저장** — LOG_DIR 환경변수로 활성화, {service}.log(전체 10MB×5) + {service}-error.log(ERROR+ 10MB×3), 4개 백엔드 12파일 변경 |
| `20260225_1112_MA_Sprint4_5_Implementation_and_Review.md` | **MA Sprint 4~5 구현 + 코드 검증** — 3기능(매수자 필터, 녹음 변환 STT+LLM, 클라이언트 포털), 12 신규파일, 3-에이전트 검증, High 2+Medium 4 보안 수정 |
| `20260225_1505_Cross_Module_Analytics_Activity_Log_Review_Fix.md` | **Cross-Module Analytics & Activity Log 리뷰 + 버그 수정** — 4개 백엔드 audit 통합 검증, 3-에이전트 리뷰 + 수동 교차 검증, Agent 허위 양성 4건 기각, P0 2건 + P1 1건 수정, Docs KPI 전역 엔드포인트 신설 |
| `20260225_2056_Financial_Model_Feature_Implementation_Report.md` | **재무모델(Financial Model) 구현 리포트** — 15파일 2,660 LOC, 코드 리뷰 4.7/5 전체 수정, Celery 태스크 큐 전환(4곳), 체크리스트 워크플로우, 472 tests 통과 |
| `20260226_2212_VDR_Azure_Blob_Storage_Migration_Plan.md` | **VDR Azure Blob Storage 마이그레이션 플랜** — Docker 로컬 볼륨 → Azure Blob, 7파일 수정+2신규, SAS URL 다운로드, IM HTTP 전환, 로컬 폴백, 월 $1~5 |

## code-review/ (24)

| 파일명 | 설명 |
|--------|------|
| `20260213_0835_FDD_Code_Review.md` | FDD 모듈 코드 리뷰 (Session 1) |
| `20260213_0837_KIIS_Code_Review.md` | KIIS 모듈 코드 리뷰 (Session 1) |
| `20260213_0908_Code_Review_Prompts.md` | 코드 리뷰 프롬프트 V1 |
| `20260213_0928_KIIS_Code_Review_Session3.md` | KIIS 코드 리뷰 (Session 3) |
| `20260213_0929_FDD_Code_Review_Session2.md` | FDD 코드 리뷰 (Session 2) |
| `20260213_1001_Platform_Code_Review.md` | 플랫폼 공통 코드 리뷰 |
| `20260213_1005_IM_Module_Code_Review.md` | IM 모듈 코드 리뷰 |
| `20260213_1223_Platform_Code_Review_Supplement.md` | 플랫폼 코드 리뷰 보충 |
| `20260213_1229_FDD_Code_Review_Session3.md` | FDD 코드 리뷰 (Session 3) |
| `20260213_1242_Code_Review_Prompts_V2.md` | 코드 리뷰 프롬프트 V2 |
| `20260213_1255_Verified_Code_Review.md` | Verified Claim Protocol 기반 리뷰 |
| `20260213_1401_Code_Review_Prompts_V3.md` | 코드 리뷰 프롬프트 V3 |
| `20260213_1416_IM_Backend_Pipeline_Code_Review.md` | IM 백엔드 파이프라인 리뷰 |
| `20260213_1457_Phase1_Code_Review_Report.md` | Phase 1 코드 리뷰 리포트 |
| `20260213_1519_Phase2_Code_Review_Report.md` | Phase 2 코드 리뷰 리포트 |
| `20260213_1546_Phase3_Code_Review_Report.md` | Phase 3 코드 리뷰 리포트 |
| `20260213_1817_Phase4_Code_Review_Report.md` | Phase 4 코드 리뷰 리포트 |
| `20260216_1911_Code_Review_Architecture_Redesign.md` | 코드 리뷰 시스템 아키텍처 재설계 |
| `20260216_1954_Code_Review_Execution_Plan.md` | 코드 리뷰 실행 계획 |
| `20260216_2011_App_Quick_Code_Review.md` | App 빠른 코드 리뷰 |
| `20260216_2031_KIIS_Module_Code_Review.md` | KIIS 모듈 코드 리뷰 (최신) |
| `20260216_2148_Full_Code_Review.md` | 전체 프론트엔드 코드 리뷰 (최종) |
| `20260223_1212_VCP_Self_Challenge_Update.md` | VCP v1.2 — Self-Challenge(3.5단계) 추가 및 review-verifier 에이전트 생성 |
| `20260223_1214_Docs_MA_Full_Code_Review.md` | Docs + MA 모듈 전체 코드 리뷰 (48파일, VCP v1.1, 12건 수정 완료) |
| `20260223_1339_Deal_Document_Studio_Code_Review.md` | Deal Document Studio 세부 코드 리뷰 (P0~P2, 15건 수정 완료 — 경로 탐색 방어, 소유권 검증, Pydantic 검증, a11y, 커스텀 예외 분리) |
| `20260223_1349_Deal_Document_Studio_Verified_Review.md` | **검증 완료** — Explore 에이전트 7개 파일 직접 확인, 라인 번호 수준 100% 일치 확인 |
| `20260224_1119_Backend_Codebase_Review.md` | **백엔드 4개 모듈 종합 평가 + 허위 리뷰 검증** — FDD/deal-mgmt/KIIS/IM 8개 카테고리 평가, 18건 주장 검증 (정확 78%, 허위 양성 1건), 최종 8.3/10 |
| `20260225_0146_MA_Meeting_Log_Code_Review_Fixes.md` | **MA 미팅 로그 코드 리뷰 수정 보고서** — 17개 이슈 전량 수정 (Critical 2 + Major 7 + Moderate 8) + 빌드 에러 ~12건, 27/27 테스트 + 빌드 성공 |
| `20260225_2033_LDD_Module_Code_Review_and_Fixes.md` | **LDD 모듈 종합 코드 리뷰 + 수정** — 12건 전량 수정 (Critical 1 + Major 4 + Moderate 5 + Minor 2), `_merge_ai_results()` 헬퍼 추출, Path Traversal 방어, Docs 타입 동기화, tsc+AST 통과 |
| `20260225_2039_IM_Module_Code_Review_and_Fix_Report.md` | **IM 모듈 종합 코드 리뷰 + 수정** — 14건 중 12건 수정 (Critical 1 + Major 3 + Moderate 5 + Minor 3), 허위 양성 3건 제거, format_utils 통합, 커스텀 예외 도입, tsc+vite build 통과 |
| `20260225_2113_IM_Module_Design_Visualization_Code_Review_Prompt.md` | **IM 모듈 디자인/시각화 특화 코드 리뷰 프롬프트** — 7개 섹션(컬러/폰트/레이아웃/차트/FE UX/BE API/통합), VCP 필수 적용, 이전 리뷰 정합성 확인, 허위 양성 방지 강화, 디자인 시스템 건강도 점수 |
| `20260225_2136_RFI_Module_Code_Review_Prompts.md` | **RFI 모듈 코드 리뷰 프롬프트** — 세션 A(백엔드 11파일, 8관점) + 세션 B(프론트엔드 6파일, 7관점) |
| `20260225_2136_RFI_Module_Backend_Code_Review.md` | **RFI 백엔드 코드 리뷰 리포트** — 26건 (Critical 2 + Major 7 + Moderate 13 + Minor 4), 거부 가설 5건 |
| `20260225_2136_RFI_Module_Frontend_Code_Review.md` | **RFI 프론트엔드 코드 리뷰 리포트** — 23건 (Major 1 + Moderate 12 + Minor 10), FE↔BE 정합성, 접근성 |

## security/ (2)

| 파일명 | 설명 |
|--------|------|
| `20260216_2025_Security_Code_Review.md` | 보안 코드 리뷰 |
| `20260216_2205_JWT_HTTPOnly_Cookie_Migration_Plan.md` | JWT → httpOnly 쿠키 마이그레이션 계획 |

## deployment/ (14)

| 파일명 | 설명 |
|--------|------|
| `20260213_1900_Deployment_Checklist.md` | 배포 전 체크리스트 |
| `20260217_0028_Session22_Build_Deploy_Report.md` | Session 22 빌드/배포 리포트 |
| `20260217_1908_Dev_Port_5173_vs_3000.md` | 개발환경 포트 가이드 |
| `20260223_1227_Production_Deployment_Guide.md` | 프로덕션 배포 가이드 (Session 34 검증 결과 추가) |
| `20260226_0011_Azure_VM_Production_Deployment_Report.md` | Azure VM 프로덕션 배포 리포트 — 18개 컨테이너, 마이그레이션, 시드 |
| `20260226_1018_CICD_Auto_Deploy_Setup.md` | CI/CD 자동 배포 설정 가이드 — GitHub Actions, Secrets, 트리거, 사용법 |
| `20260226_1119_Production_Dashboard_Error_Fix.md` | **프로덕션 대시보드 에러 수정** — KIIS JWT_SECRET 불일치, deal-mgmt Alembic 체인 단절+중복 인덱스, IM 테이블 누락, nginx DNS 캐시 |
| `20260226_1139_Production_CORS_JWT_DB_Password_Fix.md` | **CORS/JWT/DB 비밀번호 수정** — IM JWT_SECRET 추가, KIIS CORS 변수명 수정, .env JSON 배열 형식, PG 볼륨 비밀번호 동기화 |
| `20260226_1231_ERROR_CATALOG.md` | **프로덕션 에러 카탈로그** — 15개 카테고리(401~SSL만료~디스크풀), 2/26 사례, 점검 명령어, 통합 진단 스크립트 연동 |
| `20260226_1237_Production_Diagnostic_System.md` | **프로덕션 통합 진단 시스템 구축** — 10개 카테고리 진단 스크립트, Claude 규칙, deploy.yml 강화, 에러 카탈로그 |
| `20260226_1254_CICD_Health_Check_SSL_Fix.md` | **CI/CD 헬스체크 SSL 수정** — nginx SSL 리다이렉트로 localhost 헬스체크 실패, docker exec 직접 호출로 해결, 재시도 로직 추가 |
| `20260226_1330_Clova_STT_API_Key_Setup.md` | **Clova Speech STT API 키 설정** — config.py 필드 추가, docker-compose 매핑, 프로덕션 SSH 배포 |
| `20260226_1429_FDD_MA_502_Fix.md` | **FDD/MA 502 Bad Gateway 수정** — BuildKit 이미지 스왑 재발(--no-cache 복원), workers 4→2, 안정성 재확인+로그 캡처, IM revision ID 32자 제한 |
| `20260226_1544_Deploy_Pipeline_Stabilization.md` | **배포 파이프라인 영구 안정화** — 근본 원인 3가지(이미지 스왑/Alembic 3중 실행/안전장치 부재) 수정, KIIS entrypoint alembic 제거, IM HealthResponse 확장, deploy.yml 8단계 강화, 프로덕션 IM DB stamp+복구, infra-freeze/code-freeze 규칙 |
| `20260226_1839_TS_Build_Safety_Net_and_KIIS_OpenAPI_Review.md` | **KIIS OpenAPI 코드 리뷰(2차) + TS 빌드 안전장치** — @cache model 역직렬화 버그 수정, TS2352 배포 에러 수정, Husky pre-push 훅 + ci.yml feat/** 트리거 확장 |
| `20260226_2332_VDR_Azure_Blob_Storage_Deployment.md` | **VDR Azure Blob Storage 배포 완료** — Docker 볼륨→Azure Blob 마이그레이션, Storage Account 생성, 프로덕션 배포, 거래별 6레이어 분리 검증 |

## fdd/ (4)

| 파일명 | 설명 |
|--------|------|
| `20260217_0200_MultiLLM_Industry_Prompt_Improvement_Plan.md` | 멀티LLM 산업별 프롬프트 개선 |
| `20260217_0241_FDD_Workflow_Analysis.md` | FDD 워크플로 분석 |
| `20260217_1340_FDD_Template_SlotFill_System_Plan.md` | FDD 템플릿 Slot-Fill 시스템 계획 |
| `20260226_0942_FDD_Phase1-5_Code_Review.md` | FDD Big 4 WP Phase 1~5 코드 리뷰 보고서 |
| `20260226_1232_FDD_Report_Generator_Local_vs_Azure_Audit.md` | **FDD 보고서 생성기 로컬 vs Azure 비교 감사** — P0 PPTX URL 버그 수정, 에이전트 허위 보고 검증, 15개 include 플래그 API 노출, Auto FDD 상위 집합 확인 |

## kiis/ (12)

| 파일명 | 설명 |
|--------|------|
| `20260210_2250_Phase2_KIIS_Implementation_Plan.md` | KIIS Phase 2 구현 계획 |
| `20260217_0238_KIIS_Workflow_Analysis_Plan.md` | KIIS 워크플로 분석 계획 |
| `20260217_1153_KIIS_FundDetailPage_Enhancement_Plan.md` | KIIS 펀드 상세 페이지 개선 계획 |
| `20260217_1823_KIIS_Fund_Search_Audit_and_Fix.md` | KIIS 펀드 검색 감사 및 수정 |
| `20260217_1826_KIIS_Fund_Search_API_Research.md` | KIIS 펀드 검색 API 리서치 |
| `20260217_1849_KIIS_Qualitative_Reputation_Tendency_Plan.md` | 정성적 평판·투자성향 분석 계획 |
| `20260217_1853_KOFIA_Caching_System.md` | KOFIA 3계층 캐싱 시스템 구현 |
| `20260217_1905_KIIS_Qualitative_Reputation_Tendency_Implementation.md` | 정성적 평판·투자성향 분석 구현 보고서 |
| `20260217_2039_KOFIA_ProFrame_API_Migration.md` | KOFIA ProFrame API 마이그레이션 |
| `20260217_2154_GP_Centric_Search_Implementation.md` | GP(운용사) 중심 검색 전환 구현 보고서 |
| `20260222_1635_Private_Fund_GP_Datasource_Research.md` | 기관전용 사모펀드 GP 데이터소스 조사 |

## im/ (9)

| 파일명 | 설명 |
|--------|------|
| `20260212_1700_IM_FE_BE_Mismatch_Audit.md` | IM 프론트/백엔드 불일치 감사 |
| `20260217_0239_IM_Workflow_Analysis.md` | IM 워크플로 분석 |
| `20260217_1330_IM_Template_SlotFill_System_Plan.md` | IM 템플릿 Slot-Fill 시스템 계획 |
| `20260217_1342_IM_Visualization_Auto_Generation.md` | IM 시각화 자동 생성 계획 |
| `20260223_0005_Deal_Document_Studio_Integration_Review.md` | Deal Document Studio TM 통합 코드 리뷰 |
| `20260223_1128_PPT_Design_Style_Selection_Implementation.md` | PPT 디자인 스타일 선택 기능 구현 보고서 (AMIC / AMIC x 파트너 브랜딩) |
| `20260226_1521_TM_DM_Design_System_Manual.md` | **TM/DM PPT 디자인 시스템 매뉴얼 (보정판)** — 4개 PPTX XML 파싱 재분석, 5개 보정사항(섹션바 #0F3A32, 테이블 테두리 solid/dash, TOC 좌표, 재무 Y=3.325cm, 커버 줄간격 90%), 디자인 토큰·빈 템플릿 재생성 |
| `20260226_1542_TM_DM_Design_System_Deliverables.md` | **TM/DM 디자인 시스템 산출물 생성 보고서** — 5개 보정사항 상세, 수정 파일 6종, TOC 좌표 검증 결과 포함 |
| `20260226_1541_TM_DM_Generator_Implementation.md` | **TM/DM 생성기 구현 보고서** — shape_bottom_inches 크래시 수정, DM 6개 렌더러+프롬프트 신규, TM render_html 수정, 107 tests (TM 60+DM 47) |

## frontend/ (8)

| 파일명 | 설명 |
|--------|------|
| `20260211_1551_통합_프론트엔드_구현_계획.md` | 통합 프론트엔드 구현 계획 |
| `20260211_2104_UI_Refresh_Plan.md` | UI 리프레시 (dealroom.net 스타일) 계획 |
| `20260217_1610_MSW_Auth_Handler_Fix.md` | MSW 인증 핸들러 수정 |
| `20260217_2038_MSW_Removal_and_KIIS_Search_Fix.md` | MSW 제거 및 KIIS 검색 수정 |
| `20260222_1920_GSAP_Motion_System_Implementation.md` | GSAP 모션 시스템 도입 구현 보고서 (Phase 1~4 완료) |
| `20260224_1944_Team_Page_Sidebar_Menu_Extraction.md` | Our Team 섹션 → 사이드바 독립 메뉴(`/team`) 분리 |
| `20260225_1204_Deal_Document_Studio_Dashboard_Redesign.md` | Deal Doc Studio 대시보드 리디자인 — MA 거래 중심 전환, 아이콘 단색화, 표준 레이아웃 |
| `20260225_1648_Login_Export_Calendar_MA_Transition.md` | **로그인 리다이렉트 수정 + 세션 쿠키 전환 + Export Hub MA 추가 + Calendar MA 전용 전환** (14파일, tsc+build PASS) |
| `20260225_1809_Sidebar_ModuleGroup_Redesign.md` | **사이드바 ModuleSwitcher 드롭다운 → ModuleGroup 직접 노출** — 4개 모듈 독립 토글, 좌측 연결선, 0.5초 트랜지션, localStorage 상태 보존 |

## ldd/ (1)

| 파일명 | 설명 |
|--------|------|
| `20260226_1340_LDD_Report_Generation_Process.md` | LDD 보고서 작성 로직 상세 프로세스 — 3가지 생성 모드, DDRL 10개 섹션 52항목, 멀티 LLM 10단계 파이프라인, Ralph Loop 2회 적용, DOCX 렌더링, 비용 추적 |

## testing/ (2)

| 파일명 | 설명 |
|--------|------|
| `20260212_0944_Browser_E2E_Deep_Test_Plan.md` | 브라우저 E2E 딥 테스트 계획 |
| `20260224_1346_Regression_Prevention_Implementation.md` | **회귀 오류 방지 4레이어 구현 보고서** — safe-parse 방어 코딩, 67개 테스트, auth guard, 마이그레이션 타임아웃, CI 게이트 (158/158 통과) |

---

## 파일명 규칙

- **형식**: `YYYYMMDD_HHMM_{주제}.md`
- **타임스탬프 기준**: 작성 시점이 아닌 **마지막 수정 시점**
- **수정 시 갱신**: 문서 수정 시 파일명 타임스탬프를 수정 시점으로 변경
- **시간 확인**: PowerShell `Get-Date -Format "yyyyMMdd_HHmm"`
- **예외**: `INDEX.md`, `CLAUDE.md`, `CLAUDE.local.md`, `README.md`, `MEMORY.md`

## 문서 분류 기준

| 카테고리 | 저장 폴더 | 키워드 |
|---------|----------|--------|
| 전체 아키텍처/통합 계획 | `architecture/` | 통합, 구조, 포털, 설정, 전체 |
| 코드 리뷰/감사 | `code-review/` | Code Review, 리뷰, 리포트, 프롬프트 |
| 보안/인증 | `security/` | Security, JWT, 인증, XSS, CORS |
| 배포/인프라 | `deployment/` | Deploy, 배포, 빌드, CI/CD, Docker |
| FDD 모듈 전용 | `fdd/` | FDD, 실사, Due Diligence |
| LDD 모듈 전용 | `ldd/` | LDD, 법률실사, Legal Due Diligence, DDRL |
| KIIS 모듈 전용 | `kiis/` | KIIS, 펀드, REIT, 공시 |
| IM 모듈 전용 | `im/` | IM, 투자설명서, Information Memorandum |
| 프론트엔드 공통 | `frontend/` | UI, UX, 컴포넌트, MSW, 프론트엔드 |
| IM 모듈 전용 | `im/` | IM, 투자설명서, Information Memorandum, PPT 브랜딩, 디자인 토큰 |
| 테스트 | `testing/` | E2E, 테스트, Playwright, Vitest |
