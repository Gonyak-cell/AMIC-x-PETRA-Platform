# Ralph Loop로 M&A IM/TM 자동 생성 품질을 혁신하는 방법

Ralph Loop — Geoffrey Huntley가 만든 Bash 기반 자율 반복 개발 방식 — 은 **"외부 검증 + 매 반복 새 컨텍스트 + 파일 기반 상태 유지"** 라는 세 가지 원칙으로 비결정적 AI 출력물의 품질을 결정적 수준으로 끌어올린다. 이 패턴을 PPTX 형태의 IM/TM 자동 생성에 적용하면, python-pptx 프로그래밍 검증과 LLM-as-Judge 다차원 평가를 품질 게이트로 결합하여, **Investment Bank 수준의 보고서를 사람 개입 없이 반복 개선**할 수 있다. 핵심은 PRD.md에 슬라이드별 수용 기준을 정의하고, PROMPT.md에 IB급 품질 규칙을 내장하며, 자동화된 검증 파이프라인을 Stop Hook의 완료 판정 조건으로 연결하는 것이다. PPTAgent의 PPTEval 프레임워크가 이미 프레젠테이션 품질 평가에서 인간 평가 대비 **Pearson 상관계수 0.71**을 달성했고, Self-Refine 방법론은 단일 생성 대비 **약 20% 품질 향상**을 입증했다.

---

## Ralph Loop의 핵심 메커니즘과 IM/TM 적용 아키텍처

Ralph Loop의 본질은 놀랍도록 단순하다. `while :; do cat PROMPT.md | claude -p ; done` — 이 한 줄의 Bash 루프가 전부다. 매 반복마다 AI 에이전트는 **완전히 새로운 컨텍스트**에서 시작하여 디스크의 파일 상태를 읽고, 미완료 작업을 찾아 실행하고, 품질 검증을 통과하면 결과를 커밋한다. 이전 반복의 기억은 `progress.txt`와 git 히스토리에만 존재한다. 에이전트가 작업 완료를 선언하면(exit 시도), **Stop Hook**이 출력에서 사전 정의된 Completion Promise(`<promise>COMPLETE</promise>`)를 검색한다. 발견되지 않으면 루프가 자동 재시작된다.

이 패턴을 IM/TM 생성에 적용하면 다음과 같은 아키텍처가 된다. 외부 루프(Ralph Loop)가 매 반복마다 AI 에이전트를 새로 생성하고, 에이전트는 PRD.md에서 다음 미완성 슬라이드/섹션을 찾는다. python-pptx로 해당 슬라이드를 생성하거나 수정한 후, **이중 품질 게이트**를 통과해야 한다. 첫 번째 게이트는 프로그래밍 검증(구조, 수치, 디자인 일관성)이고, 두 번째는 LLM-as-Judge 평가(콘텐츠 품질, 내러티브 흐름, 시각적 전문성)다. 두 게이트를 모두 통과하면 해당 섹션이 `passes: true`로 마킹되고, 실패하면 피드백이 `progress.txt`에 기록되어 다음 반복의 개선 지침이 된다.

**Multi-Agent Ralph Loop** 변형이 IM/TM에 특히 적합하다. 전문 서브에이전트를 역할별로 분리하면 — ralph-writer(콘텐츠 생성), ralph-designer(레이아웃/차트), ralph-validator(품질 검증), ralph-researcher(시장 데이터 수집) — 각 에이전트가 자신의 전문 영역에서 최적의 결과를 낼 수 있다. Goose 프레임워크의 worker/reviewer 패턴처럼, **생성 모델과 평가 모델을 다른 모델 패밀리로 분리**하면 자기편향(self-preference bias)을 줄이고 평가 신뢰도를 높일 수 있다.

---

## python-pptx 기반 프로그래밍 품질 게이트 설계

프로그래밍 검증은 Ralph Loop의 첫 번째 품질 게이트로, LLM 호출 없이 밀리초 단위로 실행되는 빠른 필터다. python-pptx 1.0.0의 API를 활용하여 다섯 가지 핵심 검증 레이어를 구축한다.

**구조 검증 레이어**는 TM의 24-25 슬라이드, IM의 약 59 슬라이드가 올바른 순서로 존재하는지 확인한다. `slide.shapes.title` 속성으로 각 슬라이드 제목을 추출하고, PRD.md에 정의된 예상 제목 시퀀스(Cover → Disclaimer → TOC → Executive Summary → ...)와 비교한다. 섹션 구분 슬라이드의 존재 여부, 필수 구성요소(Disclaimer, Contact Page, Confidentiality 마킹)의 누락도 이 단계에서 검출한다.

**텍스트 완전성 검증**은 모든 텍스트 프레임을 순회하며 `[INSERT HERE]`, `TBD`, `XXX`, `Lorem ipsum` 등의 플레이스홀더 패턴을 정규식으로 탐지한다. python-pptx에서 `shape.has_text_frame`으로 텍스트 프레임 존재를 확인하고, `shape.text_frame.paragraphs`를 순회하며 각 `paragraph.text`를 검사한다. 빈 텍스트 박스, Source/Note 필드의 미작성, 각주 누락도 이 레이어에서 잡는다.

**재무 테이블 수치 정합성 검증**이 가장 중요하다. IB 업계에서 **반올림 오차 하나가 거래를 무산**시킬 수 있기 때문이다. `shape.has_table`로 테이블을 식별한 후 `table.cell(row, col).text`로 셀 데이터를 추출한다. 재무제표(손익계산서, 재무상태표)에서 "합계" 행이 세부 항목의 합과 일치하는지, Revenue → EBITDA → Net Income의 워터폴 계산이 맞는지, 슬라이드 간 동일 수치의 일관성(Executive Summary의 매출 vs. 재무제표 섹션의 매출)을 교차 검증한다. 괄호 표기 음수`(100)`, 통화 기호`$`, 퍼센트`%`, 천단위 쉼표를 파싱하는 유틸리티 함수가 필수적이다.

**차트 데이터 유효성 검증**에서는 `shape.has_chart`로 차트를 식별하고, `chart.plots[0].categories`로 카테고리를, `plot.series[0].values`로 데이터 값을 추출한다. None 값(누락 데이터), 카테고리-값 개수 불일치, 빈 시리즈를 검출한다. 차트 제목(`chart.has_title`), 범례(`chart.has_legend`), 다중 시리즈 차트의 범례 필수 존재 여부, 축 레이블 유무도 확인한다.

**디자인 일관성 검증**은 모든 `run.font` 속성(name, size, bold, color.rgb)을 수집하여 허용된 폰트 목록(Arial, Calibri 등)과 브랜드 컬러 팔레트 이외의 값이 사용되었는지 확인한다. 제목 shape의 `left`, `top`, `width` 포지션이 슬라이드 간 **Inches(0.1) 이내**의 오차로 일관되는지, 페이지 번호와 Confidentiality 푸터가 모든 슬라이드에 존재하는지 검증한다. 주의할 점은 `font.name`이 테마에서 상속될 때 `None`을 반환하므로, 슬라이드 마스터의 XML(`<a:majorFont>`, `<a:minorFont>`)까지 파싱해야 실효 폰트를 확인할 수 있다는 것이다.

---

## LLM-as-Judge 다차원 평가 프레임워크

프로그래밍 검증만으로는 "기술적으로 올바르지만 투자자를 설득하지 못하는" 문서를 걸러낼 수 없다. 두 번째 품질 게이트인 LLM-as-Judge는 콘텐츠 품질, 내러티브, 디자인, 데이터 활용의 **네 가지 차원**으로 문서를 평가한다.

**콘텐츠 품질 평가(가중치 35%)**에서는 LLM 판정자가 추출된 텍스트를 기반으로 Executive Summary의 완전성, 투자 논리(investment thesis)의 명확성과 설득력, 시장 분석의 TAM/SAM/SOM 방법론 적정성, 경쟁 환경 분석 깊이, 성장 전략의 구체성(단순히 "마케팅 확대"가 아닌 "헬스케어 수직시장 $50M 진입을 위한 2인 영업팀 신설")을 평가한다. G-Eval 방식의 chain-of-thought + 확률 가중 스코어링이 가장 높은 인간-모델 상관관계를 보여준다.

**내러티브 및 구조 평가(가중치 25%)**는 문서 전체의 논리적 흐름을 검증한다. IM/TM은 단순한 정보 나열이 아니라 **투자 스토리**여야 한다. 섹션 간 전환의 자연스러움, Executive Summary에서 제시된 투자 하이라이트가 후속 섹션에서 충분히 뒷받침되는지, 재무 데이터와 정성적 서술의 일관성, 리스크-기회의 균형 잡힌 프레이밍을 평가한다. PE 바이어는 Executive Summary만 읽고 나머지 50페이지를 읽을지 결정하므로, 이 섹션의 품질 기준이 특히 엄격해야 한다.

**디자인 및 시각 품질 평가(가중치 25%)**에서는 PPTX 슬라이드를 LibreOffice headless 모드(`libreoffice --headless --convert-to pdf`)로 PDF 변환 후 pdf2image로 PNG 이미지화하고, **비전 모델(GPT-4o, Claude Vision, Gemini 2.5 Pro)**에 전달한다. 최근 연구(arxiv 2508.19289)에 따르면 7가지 전문가 기반 시각 메트릭(여백, 색채, 엣지 밀도, 명도 대비, 텍스트 밀도, 색상 조화, 레이아웃 균형) + CLIP-ViT 임베딩의 조합이 인간 평가 대비 **Pearson 상관 0.83**을 달성했다. 비전 모델은 전반적 전문성, 레이아웃 균형, 색상 조화를 잘 평가하지만, 정밀한 좌표 비교나 폰트 크기 측정에는 약하므로 python-pptx 검증과 상호보완적이다.

**데이터 및 근거 평가(가중치 15%)**는 시장 데이터의 출처 명시 여부, 재무 테이블의 단위·기간 명확성, 성장률 계산의 정확성, 역사적 데이터와 예측치의 시각적 구분(음영 또는 구분선) 여부를 확인한다.

각 차원에서 1-5점 척도로 평가하며, **가중 합산 4.0/5.0 이상이면 배포 가능(Pass)**, 3.0-3.9이면 경미한 수정 필요(Conditional Pass), 3.0 미만이면 대폭 재작업(Fail)으로 판정한다. 개별 기준 중 하나라도 2.0 미만이면 자동 플래그한다. 특히 재무 수치 정확성과 내부 모순 부재는 점수와 무관하게 **반드시 통과해야 하는 절대 기준**이다.

---

## PROMPT.md와 PRD.md를 IM/TM 생성에 맞춤화하는 실전 설계

**PRD.md(제품 요구사항 문서)**는 IM/TM의 전체 청사진이다. JSON 형태의 구조화된 포맷이 관리에 유리하다. 각 슬라이드를 하나의 "유저 스토리"로 정의하고, 수용 기준과 완료 상태를 포함한다.

```json
{
  "document_type": "TM",
  "target_slides": 25,
  "sections": [
    {
      "id": "S01",
      "title": "Cover Page",
      "required_elements": ["project_name", "confidentiality_marking", "advisor_logo"],
      "acceptance_criteria": "프로젝트 코드명 표시, 'Strictly Private & Confidential' 문구, 자문사 로고 해상도 300dpi 이상",
      "passes": false
    },
    {
      "id": "S04",
      "title": "Executive Summary",
      "required_elements": ["investment_thesis", "key_financials_table", "business_model_summary"],
      "acceptance_criteria": "3개 이상 투자 하이라이트 포함, Revenue/EBITDA/마진 테이블 존재, 합계 수치 정합성 통과",
      "quality_gate": {
        "programmatic": ["table_totals_match", "no_placeholder_text", "font_compliance"],
        "llm_judge": ["investment_thesis_clarity >= 4", "financial_data_presentation >= 4"]
      },
      "passes": false
    }
  ]
}
```

**PROMPT.md**에는 IB급 품질 규칙을 명시적으로 내장해야 한다. 핵심 지시사항은 다음과 같다. PRD.md를 읽고 `passes: false`인 첫 번째 섹션을 찾아 작업한다. 작업 완료 후 품질 검증 스크립트(`python validate_pptx.py output.pptx`)를 실행하고, 모든 검증을 통과해야만 progress.txt에 기록하고 해당 섹션의 상태를 업데이트한다. 모든 재무 수치는 소스 데이터와 교차 검증한다. 차트는 반드시 2D로만 생성하고 3D 효과를 사용하지 않는다. 허용 폰트는 Arial과 Calibri뿐이다. 모든 차트와 테이블에 Source 각주를 포함한다. CIM에 특정 밸류에이션을 절대 포함하지 않는다(경쟁 입찰을 유도해야 하므로). 역사적 데이터와 예측치를 시각적으로 구분한다.

**AGENTS.md**는 반복 과정에서 발견된 패턴과 함정을 축적하는 "조직 기억"이다. 예컨대 "python-pptx에서 테마 폰트 상속 시 font.name이 None을 반환하므로, 폰트 검증 시 마스터 슬라이드 XML까지 파싱해야 함", "표의 합계 행 검증에서 소수점 반올림 오차 허용 범위는 0.01 이내", "슬라이드 12-15의 시장 드라이버 차트는 반드시 막대+선 콤보 차트로 생성" 같은 구체적 교훈이 기록되어 다음 반복에 즉시 활용된다.

**STEERING.md**는 루프 실행 중 긴급 수정이 필요할 때 사용한다. 예를 들어 클라이언트가 최신 분기 실적을 보내왔다면, 이 파일에 "Q3 2025 재무 데이터를 data/q3_2025.json에서 읽어 모든 관련 테이블과 차트를 업데이트하라"고 기록하면 다음 반복부터 에이전트가 이를 우선 처리한다.

---

## Investment Bank 수준의 품질 기준을 자동 검증에 매핑하기

Bulge bracket IB(Goldman Sachs, Morgan Stanley, JP Morgan)의 IM/TM 품질 기준은 자동 검증 시스템의 구체적 규칙으로 변환되어야 한다. 이 매핑이 Ralph Loop 성공의 핵심이다.

**디자인 절대 규칙**은 IB 업계에서 타협 불가능한 기준들이다. 허용 컬러 팔레트는 네이비 블루, 다크 그레이, 화이트, 블랙 + 자문사 브랜드 컬러 1-2개로 제한하며, python-pptx의 `run.font.color.rgb` 검사로 위반을 탐지한다. 모든 차트는 엄격히 2D여야 하고, 3D 효과는 IB에서 아마추어의 상징이다. 데이터 포인트의 정밀도가 중요한데, 부채비율 "3.2"와 "3.247"의 차이가 거래를 지연시킬 수 있다. Goldman Sachs는 자체 전용 폰트(Goldman Sans)를 사용할 만큼 브랜드 일관성에 엄격하며, JP Morgan은 **PMS 280 블루**를 정밀하게 준수한다. IB의 브랜드 가이드라인 문서는 40-50페이지에 달한다.

**콘텐츠 필수 요소**로는, 법적 Disclaimer가 반드시 첫 부분에 위치해야 하고, Executive Summary는 1-2페이지 이내의 완전한 투자 논리 요약이어야 한다. 성장 전략은 구체적이고 정량화되어야 하며("마케팅 확대" 같은 모호한 표현은 아마추어의 표시), 고객 집중도 분석과 key contract 조건이 포함되어야 한다. **CIM에 특정 밸류에이션을 포함하는 것은 전문가적 관점에서 명백한 실수**로, 가격 상한을 설정하여 경쟁 입찰을 방해한다. 이 모든 규칙을 PROMPT.md에 명시하면 AI 에이전트가 매 반복에서 준수한다.

**데이터 시각화 기준**도 구체적이다. 재무 테이블은 최소한의 격자선, 교대 행 음영, 숫자 우측 정렬/텍스트 좌측 정렬을 따른다. 워터폴(Waterfall) 차트는 EBITDA 브릿지와 매출 브릿지에 필수적이다. 파이 차트는 **최대 5개 세그먼트**로 제한하며, "Soccer Field" 차트(밸류에이션 범위 요약)는 IB 특유의 시그니처 시각화다. 모든 차트 하단에 Source를 소형 텍스트로 기재한다. 이러한 규칙을 python-pptx 검증과 LLM 비전 평가에 동시 매핑하면 이중 검증망이 완성된다.

---

## 결론: 실전 적용을 위한 핵심 인사이트

Ralph Loop를 IM/TM 자동 생성에 적용하는 것은 단순한 기술 통합이 아니라, **M&A 도메인 지식을 자동 검증 가능한 규칙으로 코드화하는 과정**이다. 가장 중요한 설계 원칙은 세 가지다.

첫째, **이중 품질 게이트 전략**이 필수적이다. python-pptx 프로그래밍 검증(빠르고 정확하지만 의미 판단 불가)과 LLM-as-Judge(느리고 비용이 들지만 투자 스토리의 설득력을 평가 가능)를 직렬로 배치한다. 프로그래밍 검증을 먼저 실행하여 명백한 결함을 저비용으로 걸러내고, 통과한 슬라이드만 LLM 평가로 보내면 비용을 최적화할 수 있다. 25슬라이드 TM의 전체 LLM 평가 비용은 병렬화 시 약 **$2-5, 소요 시간 2-5분**이다.

둘째, **PRD.md의 세분화 수준이 품질을 결정**한다. 슬라이드 단위가 아니라 슬라이드 내 구성요소 단위(제목 + 본문 + 테이블 + 차트 + 각주)로 수용 기준을 정의해야 한다. 재무 테이블의 합계 일치, 차트의 데이터 완전성, 텍스트의 플레이스홀더 부재가 각각 독립적 통과 조건이 되어야 한다.

셋째, **AGENTS.md를 통한 학습 축적**이 장기적 품질 향상의 핵심이다. 매 반복에서 발견된 python-pptx의 API 한계(테마 폰트 상속 시 None 반환 등), 업계 특수 규칙(CIM에 밸류에이션 미포함), 디자인 패턴(워터폴 차트의 색상 규칙)이 파일에 누적되면, 후속 반복의 첫 시도 성공률이 점진적으로 상승한다. 이것이 Geoffrey Huntley가 말한 "eventual consistency" — 궁극적 일관성 — 의 실현이다.

현재 가장 성숙한 참조 구현체는 **PPTAgent**(icip-cas/PPTAgent)로, 프레젠테이션 생성과 PPTEval 기반 평가를 통합하고 있다. 이를 Ralph Loop의 외부 반복 구조, python-pptx 검증 파이프라인, M&A 도메인 특화 PRD.md와 결합하면, AMIC Law/BNY Partners의 기존 자동 생성 도구를 IB급 품질 반복 개선 시스템으로 업그레이드할 수 있다.