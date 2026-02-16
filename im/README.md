# Auto-IM Generator

> 마지막 수정: 2026-02-11 21:44:06

## Information Memorandum 자동 생성 시스템

금융 M&A/투자 유치용 IM(Information Memorandum)을 AI로 자동 생성하는 시스템입니다.

### 주요 기능

- Open DART API를 통한 재무 데이터 자동 수집
- 계정과목 매핑 및 파생지표 자동 산출 (EBITDA, FCF 등)
- 산업별 재무 지표 계산 (SaaS ARR/MRR/NRR, 제조 OEE/수율, 헬스케어 rNPV, 물류 정시율)
- Multi-Model AI 내러티브 생성 (GPT-4o + Claude + Gemini 섹션별 라우팅, RAG 기반)
- IB 수준 PPTX/PDF 문서 자동 생성
- 브랜드 컬러 기반 디자인 테마 자동 적용
- JWT/API Key 인증 및 RBAC 권한 관리
- Celery 기반 비동기 문서 생성 파이프라인

---

### 프로젝트 현황 (2026-02-11 기준)

**전체 진행률: ~99%** — 백엔드 100% 완료, 프론트엔드 미구현

| 모듈 | 버전 | 소스 파일 | 테스트 | 상태 |
| ---- | ---- | -------- | ------ | ---- |
| Data Ingestor | v0.2.1 | 17개 | 223개 | ✅ 완료 |
| Financial Engine | v0.4.0 | 23개 | 268개 | ✅ 완료 |
| Industry Module | v0.3.0 | 14개 | 80개 | ✅ 완료 |
| Design Renderer | v0.4.0 | 58개 | 210개 | ✅ 완료 |
| Narrative Generator | v0.5.0 | 33개 | 44개 | ✅ 완료 |
| Chart Engine | v0.7.0 | 23개 | 77개 | ✅ 완료 |
| Brand Extractor | v0.8.0 | 16개 | 66개 | ✅ 완료 |
| API & Integration | v1.0.0 | 52개 | 263개 | ✅ 완료 |

**코드 통계**: 237 소스 파일 / 129 테스트 파일 / **1289 테스트 전체 통과**

#### 완료된 인프라

- ✅ 인증 라우트 (login, refresh, logout, users, api-keys)
- ✅ Alembic DB 마이그레이션 (4 테이블 초기 스키마)
- ✅ CI/CD 파이프라인 (GitHub Actions: lint → test → build → deploy)
- ✅ Docker 프로덕션 환경 (multi-stage build, 5 서비스)
- ✅ Nginx 리버스 프록시 + Gunicorn WSGI
- ✅ Industry Module (4개 산업별 KPI/차트/가중치 정의 + 재무 지표 계산기)
- ✅ Valuation & Returns (EV/EBITDA, P/E, IRR 솔버, 5-slide ValuationRenderer)
- ✅ Korea Overlay (규제/K-IFRS/노동/ESG 산업별 필터링)
- ✅ Testing Enhancement (PPTX XML 구조 검증 + Golden file 스냅샷)
- ✅ Image Optimizer (PNG 압축 + PPTX 이미지 최적화)

#### 남은 작업

- 프론트엔드 웹 UI (`docs/plans/unified-frontend-integration-plan.md` 참조)

---

### 빠른 시작

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt
playwright install

# 3. 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 4. DB 마이그레이션
alembic upgrade head

# 5. 개발 서버 실행
uvicorn src.api.main:app --reload

# Docker로 실행
docker-compose up -d
```

### 테스트 실행

```bash
# 전체 테스트
pytest tests/ -v

# 모듈별 테스트
pytest tests/test_data_ingestor/ -v
pytest tests/test_financial_engine/ -v
pytest tests/test_design_renderer/ -v
pytest tests/test_narrative_generator/ -v
pytest tests/test_industry/ -v
pytest tests/test_chart_engine/ -v
pytest tests/test_brand_extractor/ -v
pytest tests/test_api/ -v
```

### 프로젝트 구조

```text
auto-im-generator/
├── CLAUDE.md              # Claude Code 규칙
├── SPEC.md                # 시스템 사양서
├── PLAN.md                # 작업 계획
├── Dockerfile             # 프로덕션 이미지
├── docker-compose.yml     # 개발 환경 (5 서비스)
├── docker-compose.production.yml  # 프로덕션 환경
├── gunicorn.conf.py       # WSGI 서버 설정
├── alembic.ini            # DB 마이그레이션 설정
├── .github/workflows/     # CI/CD 파이프라인
│   ├── ci.yml             # lint + test + build
│   └── cd.yml             # staging + production deploy
├── alembic/               # DB 마이그레이션
│   └── versions/          # 마이그레이션 파일
├── nginx/                 # Nginx 리버스 프록시 설정
├── scripts/               # 배포 스크립트
├── src/
│   ├── data_ingestor/         # DART API, 문서 파싱, 웹 크롤링
│   ├── financial_engine/      # 재무 데이터 정규화, 파생지표 산출 + 산업별 지표
│   ├── industry/              # 산업 모듈 (tech, manufacturing, healthcare, logistics)
│   ├── narrative_generator/   # RAG 기반 내러티브 생성
│   ├── chart_engine/          # Plotly 차트, Graphviz 다이어그램
│   ├── design_renderer/       # PPTX/PDF 문서 조립
│   ├── brand_extractor/       # 로고/컬러 추출
│   └── api/                   # FastAPI 엔드포인트 (52 파일)
│       ├── routes/            # auth, users, api_keys, documents, companies, health
│       ├── security/          # JWT, RBAC, API Key
│       ├── services/          # 비즈니스 로직
│       ├── db/                # SQLAlchemy 모델
│       ├── schemas/           # Pydantic v2 스키마
│       ├── tasks/             # Celery 비동기 작업
│       └── middleware/        # CORS, Rate Limit, Logging
├── templates/             # PPTX/PDF 템플릿
├── tests/                 # 테스트 (1289개)
└── docs/                  # 문서
```
