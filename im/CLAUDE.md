# Auto-IM Generator - Claude Code Rules

> 마지막 수정: 2026-02-11 17:30:00

## Project Overview
금융 M&A/투자 유치용 Information Memorandum(IM) 자동 생성 시스템.
Python + FastAPI 백엔드, Open DART API, 웹 크롤링, LLM 기반 내러티브 생성,
python-pptx/WeasyPrint 기반 문서 렌더링.

## Tech Stack
- Language: Python 3.11+
- Web Framework: FastAPI (비동기)
- Task Queue: Celery + Redis
- DB: PostgreSQL (JSONB), Pinecone (Vector DB)
- Chart: Plotly (Kaleido 엔진으로 정적 이미지 수출)
- PPTX: python-pptx
- PDF: WeasyPrint (HTML/CSS → PDF)
- Crawling: Playwright, httpx
- AI: LangChain, OpenAI API (Claude API)
- CI/로고: Brandfetch API, Pillow, scikit-learn (K-Means)

## Project Structure
- `src/data_ingestor/` - DART API, 문서 파싱, 웹 크롤링
- `src/financial_engine/` - 재무 데이터 정규화, 파생지표 산출
- `src/industry/` - 산업 모듈 (tech_saas, manufacturing, healthcare, logistics + Korea Overlay)
- `src/narrative_generator/` - RAG 기반 내러티브 생성
- `src/chart_engine/` - Plotly 차트, Graphviz 다이어그램
- `src/design_renderer/` - PPTX/PDF 문서 조립
- `src/brand_extractor/` - 로고/컬러 추출
- `src/api/` - FastAPI 엔드포인트
- `templates/` - PPTX 마스터 템플릿
- `tests/` - pytest 테스트

## Code Style
- Python 코드는 PEP 8 준수, Black 포매터 사용
- Type hints 필수 (모든 함수 파라미터와 리턴 타입)
- Docstring은 Google style
- Import 순서: stdlib → third-party → local (isort 사용)
- 비동기 함수는 async/await 패턴 사용
- 에러 처리: 커스텀 Exception 클래스 정의하여 사용
- 환경변수는 .env 파일 + pydantic Settings 클래스로 관리

## Commands
- `pip install -r requirements.txt` - 의존성 설치
- `uvicorn src.api.main:app --reload` - 개발 서버 실행
- `pytest tests/ -v` - 전체 테스트
- `pytest tests/test_financial.py -v` - 단일 테스트 파일
- `black src/ tests/` - 코드 포매팅
- `isort src/ tests/` - import 정렬
- `mypy src/` - 타입 체크

## IMPORTANT Rules
- IMPORTANT: 재무 데이터 계산 로직은 반드시 단위 테스트를 먼저 작성한 후 구현
- IMPORTANT: DART API 키와 같은 시크릿은 절대 코드에 하드코딩하지 말 것. .env 사용
- IMPORTANT: .env, .claude/settings.local.json 파일은 절대 수정하지 말 것
- IMPORTANT: 외부 API 호출 시 반드시 에러 핸들링과 재시도 로직 포함
- IMPORTANT: 커밋 전 반드시 black, isort, mypy, pytest 실행
- IMPORTANT: 재무 수치 관련 코드 변경 시 기존 테스트 깨지지 않는지 반드시 확인
- IMPORTANT: 문서(.md, .py, .json 등) 수정 시 반드시 PowerShell로 현재 시각을 확인하고
  (`powershell -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"`) 해당 파일 상단 또는
  변경 이력 섹션에 `> 마지막 수정: YYYY-MM-DD HH:MM:SS` 형식으로 타임스탬프를 기록할 것

## Domain Knowledge

- IM = Information Memorandum: 투자유치/M&A용 기업소개서 (30~80페이지)
- 14개 핵심 섹션: Executive Summary, Company Overview, Market Analysis,
  Financial Analysis, Projections, Transaction Structure 등
- 소스 데이터: DART(전자공시시스템) API → 한국 상장기업 재무제표
- 재무 수치는 DART 원본과 정확히 일치해야 함 (절대 근사치 사용 금지)
- 금액 표기: KRW(원) 기준, 표/차트에 단위(백만원/억원) 반드시 명시
- 대단위: 억(10^8), 조(10^12)

## Agent Orchestration

- @data-collector: DART API 호출, 웹 크롤링 데이터 수집
- @financial-analyst: 재무 데이터 정규화, 비율 분석, 파생지표 산출
- @narrative-writer: LangChain 기반 14개 섹션 내러티브 생성
- @design-renderer: PPTX/PDF 문서 조립, 차트 삽입
- @compliance-checker: IM 최종 검증 (수치 정합성, 규제 준수) — 배포 전 필수
- @security-reviewer: 보안 취약점 검토 — PR/배포 전 필수
- @code-reviewer: 코드 품질/재무 로직 리뷰
- @test-runner: 테스트 실행 및 커버리지 분석
- @db-migration-reviewer: Alembic 마이그레이션 안전성 검토
- @performance-profiler: 성능 병목 분석, 최적화 제안

## Skill References (자동 참조)

아래 모듈/작업 시 반드시 해당 스킬 문서를 참조하여 표준 패턴을 따를 것.

- `src/data_ingestor/` DART API 관련 → `dart-api`, `rate-limiter`
- `src/financial_engine/` 재무 분석 → `financial-analysis`, `schema-validator`
- `src/narrative_generator/` 내러티브 → `narrative-generator`
- `src/chart_engine/` 차트/시각화 → `chart-engine`, `brand-extractor`
- `src/design_renderer/` 문서 조립 → `pptx-generator`, `template-designer`, `i18n-kr`
- `src/api/` API 엔드포인트 → `api-endpoint-builder`, `rate-limiter`
- Celery 비동기 태스크 → `celery-task`
- DB 마이그레이션 (Alembic) → `database-migration`
- 웹 크롤링 → `web-crawler`, `rate-limiter`
- 보안 관련 변경 → `security-audit`

## 작업 방식 규칙 — 컨텍스트 한계 관리

- IMPORTANT: 컨텍스트 윈도우가 부족해질 것으로 예상되면 **즉시 작업을 중단**할 것
- 중단 시 반드시 다음을 수행:
  1. 완료된 작업 목록과 미완료 작업 목록을 정리
  2. 이어가기 위한 컨텍스트 요약 (현재 상태, 다음 단계, 주의사항)
  3. `CLAUDE.local.md`에 진행 상황 기록
  4. 사용자에게 새 세션에서 이어서 작업하라고 안내
- IMPORTANT: 컨텍스트 부족 상태에서 **억지로 작업을 계속하는 것을 절대 금지**
  - 품질 저하, 중복 코드, 누락된 로직 등의 원인이 됨
  - 차라리 깔끔하게 끊고 새 세션에서 이어가는 것이 훨씬 나음

## Workflow
1. 새 기능 구현 전 PLAN.md에 계획 작성
2. 주요 변경 전 `.claude/RULES.md`의 4단계 리뷰 체크리스트 참조 (Architecture → Code Quality → Tests → Performance)
3. 테스트 먼저 작성 (TDD)
4. 구현 후 lint + typecheck + test 실행
5. git branch 생성 후 작업, main 직접 커밋 금지
6. 마일스톤 완료 시 `/review` 명령으로 종합 코드 리뷰 실행

## Review Framework

- 리뷰 규칙: `.claude/RULES.md` (4단계 Plan Mode Review)
- 프로젝트 브리프: `docs/PROJECT_BRIEF.md` (Technical Co-Founder 프롬프트)
- BIG CHANGE: 섹션별 최대 4개 이슈, 인터랙티브 진행
- SMALL CHANGE: 섹션당 1개 질문만 인터랙티브

## Testing Strategy

- 재무 계산: property-based 테스트 (Hypothesis) + 단위 테스트
- API 엔드포인트: TestClient + async 픽스처
- PPTX 출력: 슬라이드 수, 플레이스홀더 내용, 이미지 존재 검증
- PDF 출력: 페이지 수, 텍스트 추출 검증
- 크롤링: VCR cassette 또는 httpx 모킹 (CI에서 라이브 호출 금지)
- 커버리지: 재무 엔진 모듈 90% 이상 목표

## Gotchas
- python-pptx의 Inches() 단위와 Emu 단위 혼동 주의
- Plotly 정적 이미지 수출 시 kaleido 엔진 필요 (pip install kaleido)
- DART API 호출 제한: 분당 100회. Rate limiter 필수
- WeasyPrint는 시스템에 cairo, pango 라이브러리 필요
- Playwright는 첫 실행 시 `playwright install` 필요
- 한글 폰트 사용 시 NanumGothic 등 시스템에 설치 필요

## When Compacting
컴팩팅 시 반드시 보존할 정보:
- 현재 작업 중인 모듈명과 파일 목록
- 실패한 테스트 내역
- PLAN.md의 현재 진행 상태
- 최근 변경한 파일 경로들
