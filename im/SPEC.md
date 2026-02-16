# IM Auto-Generator System Specification

## 1. 시스템 개요
Information Memorandum(IM) 자동 생성 시스템은 기업의 기초 정보를 입력받아,
Open DART API, 웹 크롤링, LLM을 활용하여 IB 수준의 전문적인 IM 문서를
PPTX/PDF 형태로 자동 생성하는 AI 금융 에이전트 시스템입니다.

## 2. 핵심 모듈
| 모듈 | 역할 | 주요 기술 |
|------|------|-----------|
| Data Ingestor | DART API, 문서파싱, 웹크롤링 | httpx, PyMuPDF, Playwright |
| Financial Engine | 재무 정규화, 지표 산출 | pandas, rapidfuzz, Decimal |
| Narrative Generator | RAG 기반 텍스트 생성 | Pinecone, OpenAI, Anthropic Claude, Google Gemini (Multi-Model Routing) |
| Chart Engine | 금융 차트 시각화 | Plotly, Kaleido, Graphviz |
| Design Renderer | PPTX/PDF 문서 조립 | python-pptx, WeasyPrint |
| Brand Extractor | 로고/컬러 추출 | Brandfetch, Pillow, K-Means |
| API Backend | 웹 API, 비동기 처리 | FastAPI, Celery, Redis |

## 3. IM 표준 구성 (14개 섹션)
1. 표지 (Cover)
2. 면책조항 (Disclaimer)
3. 목차 (Table of Contents)
4. Executive Summary
5. Investment Highlights
6. 회사 개요 (Company Overview)
7. 사업 모델 (Business Model)
8. 시장 분석 (Market Analysis)
9. 재무 분석 (Financial Analysis)
10. 조직 및 경영진 (Management Team)
11. 주주 구성 (Shareholder Structure)
12. 성장 전략 (Growth Strategy)
13. 거래 구조 (Transaction Structure)
14. 부록 (Appendix)

## 4. 입력 데이터
### 필수 사용자 입력
- 기업명 (국/영문), 법인등록번호, 홈페이지 URL
- 상세 재무제표 (관리회계 기준)
- 사업부별 매출 내역, 주요 고객사 명단
- 딜 구조 (구주/신주 규모, 밸류에이션 범위)

### 자동 수집 데이터
- DART: 재무제표, 기업개황, 지분공시, 임원현황
- 웹: 뉴스, 시장 트렌드, 경쟁사 정보

## 5. 출력 형태
- PPTX (PowerPoint): 편집 가능한 프레젠테이션
- PDF: 인쇄용 고품질 문서
- 차트: 300DPI PNG 또는 SVG 벡터

## 6. 보안 요구사항
- 데이터 암호화: AES-256 (저장), TLS 1.3 (전송)
- LLM 보안: Zero Data Retention API 사용
- 접근 제어: RBAC 기반 프로젝트별 권한 관리
