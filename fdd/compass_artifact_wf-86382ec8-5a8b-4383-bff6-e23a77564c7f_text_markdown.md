# Claude Code로 M&A FDD 보고서 자동 생성: 종합 구현 가이드

**Claude Code의 Skills, Rules, Agent 시스템을 결합하면 Big 4 회계법인 수준의 Financial Due Diligence 보고서를 자동 생성하는 파이프라인을 구축할 수 있다.** 핵심은 CLAUDE.md로 프로젝트 컨텍스트를 설정하고, `.claude/skills/`에 PPTX·XLSX 생성 스킬을 배치하며, MCP 서버로 데이터소스를 연결하고, 서브에이전트가 분석-차트생성-보고서조립을 병렬 수행하는 아키텍처다. Anthropic은 이미 공식 document-skills 리포지토리(`anthropics/skills`)에서 pptx, xlsx, docx, pdf 생성 스킬을 제공하고 있으며, 이를 FDD 도메인에 맞게 커스터마이징하면 된다.

---

## 1. Claude Code의 메모리 계층과 CLAUDE.md 설정 체계

Claude Code는 세션 간 기억을 유지하지 않으므로, **CLAUDE.md 파일이 프로젝트의 영구 메모리** 역할을 한다. 이 파일은 Claude Code 실행 시 자동으로 로딩되며, 계층적 구조로 우선순위가 적용된다.

| 메모리 유형 | 위치 | 공유 범위 |
|---|---|---|
| Enterprise 정책 | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | 전체 조직 |
| 프로젝트 메모리 | `./CLAUDE.md` 또는 `./.claude/CLAUDE.md` | 팀 (소스 컨트롤) |
| 사용자 메모리 | `~/.claude/CLAUDE.md` | 개인 (모든 프로젝트) |
| 프로젝트 로컬 | `./CLAUDE.local.md` | 개인 (현재 프로젝트) |

Claude Code는 현재 디렉토리에서 루트까지 **재귀적으로** CLAUDE.md를 탐색하며, 하위 디렉토리의 CLAUDE.md는 해당 경로의 파일을 읽을 때 동적으로 로딩된다. `@path/to/file` 구문으로 외부 파일을 임포트할 수 있고, 최대 **5 depth**까지 재귀 임포트가 지원된다. FDD 프로젝트에서는 다음과 같이 구성한다:

```markdown
# FDD Report Generator — CLAUDE.md

## Project Overview
M&A Financial Due Diligence 보고서 자동 생성 시스템. 
재무 데이터를 입력받아 QoE, NWC, Net Debt 분석 후 Big 4 스타일 PPT/Excel 보고서 출력.

## Key Rules
- 모든 Excel 수식은 Python 계산이 아닌 Excel 함수(=SUM, =AVERAGE 등)로 작성
- 재무 수치는 항상 천 단위 구분기호 사용, 음수는 괄호 표기
- 차트 색상은 config/design_system.yaml의 Big 4 팔레트 준수
- 코드 스타일: Black formatter, type hints 필수, docstring Google style

## Architecture
@docs/architecture.md
@config/design_system.yaml

## Available Commands
- `python -m src.pipeline.run --deal DEAL_NAME` : 전체 파이프라인 실행
- `python -m src.analysis.qoe_engine --input data/raw/` : QoE 분석만 실행
```

**권장 사항**: CLAUDE.md는 **500줄 이내**로 유지하고, 상세 참조 자료는 Skills의 reference 파일로 분리한다. `#` 단축키로 대화 중 즉시 메모리를 추가하거나, `/init` 명령으로 프로젝트 초기 CLAUDE.md를 자동 생성할 수 있다.

---

## 2. Rules 시스템으로 모듈화된 코딩 규칙 관리

`.claude/rules/` 디렉토리의 모든 `.md` 파일은 프로젝트 메모리와 동일한 우선순위로 자동 로딩된다. 단일 CLAUDE.md보다 **주제별로 분리된 규칙 파일**이 관리에 효율적이다.

```
.claude/rules/
├── financial-conventions.md    # 재무 수치 표기 규칙
├── python-style.md             # 코딩 스타일 가이드
├── chart-standards.md          # 차트 디자인 표준
├── testing.md                  # 테스트 작성 규칙
└── pptx-generation.md          # PPT 생성 시 준수사항
```

**조건부 Rules**는 YAML frontmatter의 `paths` 필드로 특정 파일에만 적용할 수 있다:

```yaml
---
paths:
  - "src/charts/**/*.py"
---
# Chart Generation Rules
- 모든 차트는 plotly로 생성 후 PNG 300 DPI로 export
- 색상은 반드시 Big4Colors 클래스의 상수 사용
- 워터폴 차트의 증가 바는 POSITIVE_GREEN, 감소는 NEGATIVE_RED, 합계는 PRIMARY_BLUE
- Y축 라벨에 통화 단위(USD M) 항상 표시
```

```yaml
---
paths:
  - "src/report_generation/**/*.py"
---
# Report Generation Rules
- python-pptx 사용 시 반드시 template.pptx 기반으로 생성
- 모든 슬라이드에 footer: "CONFIDENTIAL", 페이지 번호, 날짜 포함
- 폰트: 제목 Arial Bold 18pt, 본문 Calibri 10pt
- 테이블 헤더: Primary Blue 배경에 White 텍스트
```

사용자 수준 규칙(`~/.claude/rules/*.md`)은 모든 프로젝트에 적용되고, 프로젝트 규칙이 더 높은 우선순위를 가진다. 심볼릭 링크로 공통 규칙을 여러 프로젝트에서 공유할 수도 있다.

---

## 3. Skills 시스템: FDD 보고서용 커스텀 스킬 구축

### SKILL.md 구조와 등록 메커니즘

Agent Skills는 Claude의 기능을 모듈 단위로 확장하는 핵심 시스템이다. 각 스킬은 `SKILL.md` 파일(YAML frontmatter + Markdown 지침)과 보조 스크립트·템플릿으로 구성된다.

| 스킬 위치 | 경로 | 범위 |
|---|---|---|
| 개인 스킬 | `~/.claude/skills/<skill-name>/SKILL.md` | 모든 프로젝트 |
| 프로젝트 스킬 | `.claude/skills/<skill-name>/SKILL.md` | 현재 프로젝트 (git 공유) |
| 플러그인 스킬 | 플러그인 `skills/` 디렉토리 | 플러그인 활성 시 |

> **참고**: `/mnt/skills/` 경로는 Claude.ai의 서버사이드 코드 실행 샌드박스 환경에서 사용되는 경로이며, Claude Code CLI에서는 위 경로들을 사용한다. Anthropic 공식 스킬은 `anthropics/skills` GitHub 리포지토리에서 관리된다.

스킬은 **프로그레시브 디스클로저** 방식으로 로딩된다. 시작 시에는 name과 description만 로딩하여 **스킬당 약 100토큰**만 소비하고, Claude가 필요하다고 판단하면 전체 SKILL.md(5,000토큰 미만)를 로딩하며, 보조 파일은 실제 사용 시점에 온디맨드로 읽힌다.

### FDD 프로젝트용 커스텀 스킬 설계

**EBITDA Bridge 워터폴 차트 스킬:**

```yaml
---
name: ebitda-waterfall
description: "EBITDA Bridge 워터폴 차트를 생성합니다. Quality of Earnings 분석에서 Reported EBITDA에서 Adjusted EBITDA까지의 조정 항목을 시각화할 때 사용합니다."
allowed-tools: Read, Write, Bash
---

# EBITDA Bridge Waterfall Chart Generator

## Instructions
1. 입력 데이터(JSON/dict)에서 카테고리명과 값 추출
2. Plotly go.Waterfall 사용하여 차트 생성
3. 색상 체계: 증가=#2E7D32(Green), 감소=#E0301E(Red), 합계=#00338D(Navy)
4. 커넥터 라인: RGB(63,63,63) 점선
5. PNG 300 DPI로 BytesIO에 저장 후 반환
6. 차트 크기: 900x500px, scale=2

## Color Constants
@scripts/colors.py

## Example
```python
from scripts.waterfall import create_ebitda_bridge

data = {
    "categories": ["Reported EBITDA", "Owner Comp", "One-time Legal", 
                    "Rent Adjustment", "Run-rate Salary", "Adjusted EBITDA"],
    "values": [8400, 350, 280, -120, -180, None],
    "measures": ["absolute", "relative", "relative", "relative", "relative", "total"]
}
chart_buffer = create_ebitda_bridge(data, title="FY2025 EBITDA Bridge ($K)")
```
```

**Quality of Earnings 테이블 스킬:**

```yaml
---
name: qoe-table
description: "Quality of Earnings 분석 테이블을 PPT 슬라이드 또는 Excel 시트로 생성합니다. Reported Net Income에서 Adjusted EBITDA까지의 조정 항목을 연도별로 정리합니다."
allowed-tools: Read, Write, Bash
---

# Quality of Earnings Table Generator

## Instructions
1. QoE 데이터(DataFrame)를 입력받아 조정 카테고리별로 그룹핑
2. 연도별 컬럼 구성 (LTM, FY-1, FY-2, FY-3)
3. 행 구조:
   - Reported Net Income (bold, border-bottom)
   - + Interest / + Tax / + D&A (indent level 1)
   - = Reported EBITDA (bold, border-top-bottom)
   - Management Adjustments 소계
   - Diligence Adjustments 소계  
   - Pro-Forma Adjustments 소계
   - = Adjusted EBITDA (bold, double border-top)
4. 음수는 괄호 표기, 양수 add-back은 초록, 마이너스 조정은 빨강
5. PPT 모드: python-pptx Table로 생성
6. Excel 모드: openpyxl로 생성 (모든 수치는 Excel 수식으로)

## Reference
@references/qoe_categories.yaml
```

**NWC 분석 차트 스킬:**

```yaml
---
name: nwc-analysis
description: "Net Working Capital 분석 차트와 테이블을 생성합니다. 월별 NWC 트렌드, 구성요소 분해, DSO/DPO/DIO 분석, NWC Peg 산출 시 사용합니다."
---

# NWC Analysis Chart & Table Generator

## Instructions
1. 월별 Balance Sheet 데이터에서 NWC 구성요소 추출
   - Current Assets: AR, Inventory, Prepaid Expenses
   - Current Liabilities: AP, Accrued Expenses, Deferred Revenue
   - 제외: Cash, Short-term Debt
2. Stacked Bar Chart: 월별 NWC 구성요소 분해
3. Line Chart Overlay: NWC 합계 트렌드
4. KPI 카드: 12개월 평균 NWC, DSO, DPO, DIO, Cash Conversion Cycle
5. NWC Peg 계산: 지난 12개월 Normalized NWC 평균
6. 계절성 패턴 식별 및 하이라이트

## Output Formats
- PPT 슬라이드 (차트 이미지 + KPI 텍스트박스)
- Excel 시트 (수식 기반 동적 모델)
```

### Anthropic 공식 Document Skills 활용

Anthropic의 `anthropics/skills` 리포지토리는 PPTX, XLSX, DOCX, PDF 생성 스킬을 공식 제공한다. FDD 프로젝트에서는 이를 기반으로 확장한다:

- **PPTX 스킬**: 템플릿 없이 새로 만들 때는 **html2pptx 워크플로우**(HTML → PPTX 변환)를 사용하고, 기존 브랜딩 템플릿이 있으면 **OOXML 직접 편집 워크플로우**(unpack → XML 수정 → repack)를 사용한다
- **XLSX 스킬**: 핵심 원칙은 **"Python 계산 금지, 반드시 Excel 수식 사용"**이다. `=SUM(B2:B9)` 형태로 작성해야 스프레드시트가 동적으로 유지된다
- **스킬 조합**: Claude는 여러 스킬을 동시에 로딩하여 "재무 분석 → 차트 생성 → PPT 조립"을 한 세션에서 수행할 수 있다

API를 통해 스킬을 활성화할 때는 `betas=["skills-2025-10-02"]`와 `container.skills` 파라미터를 사용한다.

---

## 4. Agent 시스템과 멀티에이전트 워크플로우

### 서브에이전트 구성

Claude Code는 `.claude/agents/` 디렉토리에 커스텀 서브에이전트를 정의할 수 있다. 각 서브에이전트는 **독립적인 컨텍스트 윈도우**에서 실행되며, 특정 도구와 모델을 지정할 수 있다.

```yaml
# .claude/agents/financial-analyst.md
---
name: financial-analyst
description: 재무 데이터를 분석하고 QoE, NWC, Net Debt 계산을 수행합니다
tools: Read, Write, Bash, Glob, Grep
model: sonnet
skills: ebitda-waterfall, qoe-table, nwc-analysis
---
당신은 M&A Financial Due Diligence 전문 분석가입니다.
입력된 재무 데이터에서 다음을 수행하세요:
1. Reported EBITDA 산출 (Net Income + Interest + Tax + D&A)
2. 조정 항목 식별 및 분류 (Management/Diligence/Pro-forma)
3. Adjusted EBITDA 산출
4. NWC 구성요소 분석 및 12개월 평균 산출
5. Net Debt 및 Debt-like Items 식별
모든 계산은 Excel 수식으로 작성하고, 소스 데이터 참조를 명시하세요.
```

```yaml
# .claude/agents/report-builder.md
---
name: report-builder
description: 분석 결과를 Big 4 스타일 PPT/Excel 보고서로 조립합니다
tools: Read, Write, Bash
model: sonnet
skills: pptx, xlsx, ebitda-waterfall, qoe-table
---
당신은 Big 4 회계법인 스타일의 FDD 보고서 제작 전문가입니다.
분석 엔진의 출력을 받아 다음을 생성하세요:
1. Executive Summary 슬라이드 (KPI 대시보드)
2. QoE / EBITDA Bridge 섹션 (워터폴 차트 + 상세 테이블)
3. NWC 분석 섹션 (트렌드 차트 + 구성요소 테이블)
4. Net Debt 섹션
디자인: config/design_system.yaml 참조, CONFIDENTIAL 워터마크 포함
```

### MCP 서버를 통한 데이터소스 연동

MCP(Model Context Protocol)는 Claude Code를 외부 데이터소스와 연결하는 오픈 표준이다. FDD 프로젝트에서는 다음과 같이 구성한다:

```json
// .mcp.json (프로젝트 루트 — 팀 공유)
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data/"],
      "env": {}
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "${DB_CONNECTION_STRING}"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

MCP 서버 관리는 CLI로 수행한다: `claude mcp add`, `claude mcp list`, `claude mcp remove`. 세션 중에는 `/mcp` 명령으로 연결 상태를 확인한다. 설치 스코프는 **local**(개인, 현재 프로젝트), **project**(.mcp.json, 팀 공유), **user**(개인, 전체 프로젝트) 세 가지다.

### FDD 멀티에이전트 워크플로우 아키텍처

Anthropic의 프로덕션 멀티에이전트 시스템은 **오케스트레이터-워커 패턴**을 사용한다. FDD 보고서 생성에 적용하면:

```
[사용자 요청: "Deal ABC FDD 보고서 생성"]
        ↓
[메인 에이전트 (Orchestrator)]
    ├── [financial-analyst 서브에이전트] → QoE 분석, NWC 계산, Net Debt 식별
    ├── [chart-generator 서브에이전트] → EBITDA Bridge, 트렌드 차트, 대시보드
    └── [report-builder 서브에이전트] → PPT 조립, Excel 워크페이퍼 생성
        ↓
[최종 결과 취합 및 보고서 출력]
```

각 서브에이전트는 독립 컨텍스트에서 병렬로 실행되며, 결과가 메인 에이전트로 요약되어 반환된다. `run_in_background` 파라미터로 백그라운드 실행도 가능하다. Git worktree를 활용하면 에이전트별 격리된 작업 환경을 제공할 수 있다.

---

## 5. FDD 보고서 자동 생성의 구체적 구현

### EBITDA Bridge 워터폴 차트 구현

python-pptx는 네이티브 워터폴 차트를 지원하지 않으므로, **Plotly의 `go.Waterfall`로 생성한 뒤 PNG로 슬라이드에 삽입**하는 것이 최적의 접근이다:

```python
import plotly.graph_objects as go
import plotly.io as pio
from io import BytesIO

def create_ebitda_bridge(adjustments: dict, title: str) -> BytesIO:
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=adjustments["measures"],  
        # ["absolute","relative","relative","relative","total"]
        x=adjustments["categories"],
        y=adjustments["values"],
        connector={"line": {"color": "rgb(63,63,63)", "dash": "dot"}},
        increasing={"marker": {"color": "#2E7D32"}},
        decreasing={"marker": {"color": "#E0301E"}},
        totals={"marker": {"color": "#00338D"}},
        textposition="outside",
        text=[f"${v:,.0f}" if v else "" for v in adjustments["values"]],
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(family="Arial", size=18, color="#00338D")),
        font=dict(family="Calibri", size=11),
        plot_bgcolor="white",
        showlegend=False,
        width=900, height=500,
        margin=dict(t=60, b=40, l=60, r=40),
    )
    buffer = BytesIO()
    pio.write_image(fig, buffer, format="png", scale=2)
    buffer.seek(0)
    return buffer
```

대안으로 python-pptx의 **Stacked Column Chart**에서 Base 시리즈를 투명하게 만드는 시뮬레이션 방식도 사용 가능하나, Plotly 접근이 시각적 품질과 유지보수 측면에서 우수하다.

### Big 4 디자인 시스템 구현

네 개 회계법인의 브랜드 컬러를 코드 상수로 정의하고, YAML 설정으로 교체 가능하게 한다:

```python
from pptx.dml.color import RGBColor
from dataclasses import dataclass

@dataclass
class Big4DesignSystem:
    """Big 4 회계법인 스타일 디자인 상수"""
    # KPMG 기반 (가장 범용적)
    PRIMARY: RGBColor = RGBColor(0x00, 0x33, 0x8D)    # Navy Blue
    SECONDARY: RGBColor = RGBColor(0x00, 0x5E, 0xB8)  # Medium Blue
    ACCENT: RGBColor = RGBColor(0x00, 0x91, 0xDA)     # Light Blue
    
    # 재무 컨벤션
    POSITIVE: RGBColor = RGBColor(0x2E, 0x7D, 0x32)   # Green (add-backs)
    NEGATIVE: RGBColor = RGBColor(0xE0, 0x30, 0x1E)   # Red (deductions)
    NEUTRAL: RGBColor = RGBColor(0x66, 0x66, 0x66)     # Gray
    
    # 테이블
    HEADER_BG: RGBColor = RGBColor(0x00, 0x33, 0x8D)  # Navy header
    HEADER_TEXT: RGBColor = RGBColor(0xFF, 0xFF, 0xFF) # White text
    ALT_ROW: RGBColor = RGBColor(0xF5, 0xF5, 0xF5)   # Zebra stripe
    TEXT_DARK: RGBColor = RGBColor(0x33, 0x33, 0x33)   # Body text
    
    # 타이포그래피
    FONT_HEADING: str = "Arial"      # 18-24pt Bold
    FONT_BODY: str = "Calibri"       # 10-12pt
    FONT_DATA: str = "Calibri"       # 10pt, right-aligned
```

Big 4 프레젠테이션의 공통 디자인 원칙: **16:9 와이드스크린**, 풀 너비 컬러 헤더 바, 넉넉한 여백, **최대 2-3색** 차트, 3D 효과 금지, 음수는 괄호와 빨간색, 합계는 굵은 글씨에 상단 이중 테두리, 모든 슬라이드 푸터에 "CONFIDENTIAL" 마크.

### Executive Summary 대시보드 슬라이드

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu

def create_executive_summary(prs, deal_data, design):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    
    # 헤더 바
    header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.33), Inches(0.8))
    header.fill.solid()
    header.fill.fore_color.rgb = design.PRIMARY
    
    # KPI 카드 4개 배치 (Revenue, Adj. EBITDA, EBITDA Margin, NWC Peg)
    kpi_data = [
        ("Revenue", f"${deal_data['revenue']:.1f}M", f"{deal_data['rev_growth']:+.1f}%"),
        ("Adj. EBITDA", f"${deal_data['adj_ebitda']:.1f}M", f"{deal_data['ebitda_margin']:.1f}%"),
        ("EBITDA Margin", f"{deal_data['ebitda_margin']:.1f}%", f"{deal_data['margin_delta']:+.1f}pp"),
        ("NWC Peg", f"${deal_data['nwc_peg']:.1f}M", f"12-mo avg"),
    ]
    # 각 KPI를 카드형 텍스트박스로 배치...
```

### openpyxl로 Excel 재무 모델 생성

Excel 워크페이퍼는 FDD 분석의 백본이다. Claude Code의 XLSX 스킬이 강조하는 핵심 원칙은 **모든 계산을 Excel 수식으로 유지**하는 것이다:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, NamedStyle

def create_qoe_workpaper(data, wb=None):
    wb = wb or Workbook()
    ws = wb.create_sheet("QoE Analysis")
    
    # Named Styles 정의
    header_style = NamedStyle(name='fdd_header')
    header_style.font = Font(name='Calibri', bold=True, size=11, color='FFFFFF')
    header_style.fill = PatternFill('solid', fgColor='00338D')
    header_style.alignment = Alignment(horizontal='center', vertical='center')
    wb.add_named_style(header_style)
    
    # 헤더 행
    headers = ['Description', 'FY2023', 'FY2024', 'LTM', 'Notes']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.style = 'fdd_header'
    
    # EBITDA 산출 수식 (하드코딩 절대 금지)
    ws['A3'] = 'Reported Net Income'
    ws['B3'] = data['net_income_fy23']  # 입력값만 하드코딩
    ws['A4'] = '(+) Interest Expense'
    ws['A5'] = '(+) Income Tax'
    ws['A6'] = '(+) Depreciation & Amortization'
    ws['A7'] = 'Reported EBITDA'
    ws['B7'] = '=SUM(B3:B6)'  # 반드시 수식으로
    ws['B7'].font = Font(bold=True)
    ws['B7'].border = Border(top=Side(style='double'), bottom=Side(style='double'))
    
    # 조건부 서식: 음수 빨간색
    from openpyxl.formatting.rule import CellIsRule
    ws.conditional_formatting.add('B3:D50',
        CellIsRule(operator='lessThan', formula=['0'],
                   fill=PatternFill(bgColor='FFC7CE'),
                   font=Font(color='FF0000')))
    
    return wb
```

---

## 6. 이상적인 프로젝트 폴더 구조

FDD 보고서 자동 생성 프로젝트의 전체 구조는 Claude Code의 설정 체계와 Python 모듈을 결합한 형태다:

```
fdd-report-generator/
├── CLAUDE.md                          # 프로젝트 메모리 (아키텍처, 규칙 요약)
├── CLAUDE.local.md                    # 개인 설정 (API 키 참조 등, gitignore됨)
├── .mcp.json                          # MCP 서버 설정 (팀 공유)
│
├── .claude/
│   ├── settings.json                  # 권한 규칙, 환경변수
│   ├── agents/                        # 서브에이전트 정의
│   │   ├── financial-analyst.md       # 재무 분석 전문 에이전트
│   │   ├── chart-generator.md         # 차트 생성 에이전트
│   │   └── report-builder.md          # 보고서 조립 에이전트
│   ├── skills/                        # 커스텀 FDD 스킬
│   │   ├── ebitda-waterfall/
│   │   │   ├── SKILL.md
│   │   │   └── scripts/waterfall.py
│   │   ├── qoe-table/
│   │   │   ├── SKILL.md
│   │   │   └── references/qoe_categories.yaml
│   │   ├── nwc-analysis/
│   │   │   ├── SKILL.md
│   │   │   └── scripts/nwc_calculator.py
│   │   └── exec-dashboard/
│   │       ├── SKILL.md
│   │       └── templates/dashboard_layout.json
│   └── rules/                         # 모듈화된 규칙
│       ├── financial-conventions.md
│       ├── python-style.md
│       ├── chart-standards.md
│       └── pptx-generation.md
│
├── config/
│   ├── design_system.yaml             # Big 4 색상, 폰트, 레이아웃 설정
│   ├── adjustment_categories.yaml     # QoE 조정 항목 분류 체계
│   ├── nwc_definitions.yaml           # NWC 포함/제외 계정 정의
│   └── debt_like_items.yaml           # Debt-like items 분류 기준
│
├── data/
│   ├── raw/                           # 원본 재무 데이터 (Excel/CSV)
│   ├── processed/                     # 정제된 데이터
│   └── mappings/                      # 계정과목 매핑
│       └── chart_of_accounts_map.yaml
│
├── src/
│   ├── data_ingestion/                # 데이터 수집 및 검증
│   │   ├── excel_loader.py
│   │   ├── data_validator.py
│   │   └── standardizer.py
│   ├── analysis/                      # 분석 엔진
│   │   ├── qoe_engine.py             # Quality of Earnings
│   │   ├── nwc_engine.py             # Net Working Capital
│   │   ├── net_debt_engine.py        # Net Debt & Debt-like Items
│   │   ├── revenue_engine.py         # Revenue Quality
│   │   └── ratio_engine.py           # 재무비율 KPI
│   ├── charts/                        # 차트 생성
│   │   ├── waterfall.py              # EBITDA Bridge
│   │   ├── trend_charts.py           # 트렌드 라인
│   │   └── composition.py            # Revenue Mix, 고객 집중도
│   ├── report_generation/             # 보고서 빌더
│   │   ├── pptx_builder.py           # PowerPoint 생성
│   │   ├── excel_workbook.py         # Excel 워크페이퍼
│   │   └── design_system.py          # Big 4 스타일 클래스
│   ├── commentary/                    # AI 내러티브 생성
│   │   ├── ai_narrator.py            # Claude API 연동
│   │   └── prompts/                   # 섹션별 프롬프트 템플릿
│   └── pipeline/
│       └── run.py                     # 전체 파이프라인 오케스트레이터
│
├── templates/
│   ├── pptx/fdd_master.pptx          # 브랜딩된 PPT 마스터 템플릿
│   └── excel/workpaper_template.xlsx  # Excel 템플릿
│
├── output/                            # 생성된 보고서
│   ├── reports/
│   └── workpapers/
│
└── tests/
    ├── test_qoe.py
    ├── test_nwc.py
    └── fixtures/                      # 테스트용 샘플 데이터
```

### 설정 파일 간 역할 분담

| 파일 | 역할 | 내용 |
|---|---|---|
| `CLAUDE.md` | 프로젝트 컨텍스트 | 아키텍처 개요, 핵심 규칙 요약, 자주 쓰는 명령어 |
| `.claude/rules/*.md` | 모듈화된 세부 규칙 | 파일 유형별 코딩/디자인 표준 |
| `.claude/skills/*/SKILL.md` | 재사용 가능한 기능 | 차트 생성, 테이블 생성 등 도메인 스킬 |
| `.claude/agents/*.md` | 전문 서브에이전트 | 분석, 차트, 보고서 각 담당 에이전트 |
| `.claude/settings.json` | 권한 및 환경설정 | 허용 명령어, 금지 파일 경로, 모델 지정 |
| `.mcp.json` | 외부 도구 연결 | DB, 파일시스템, GitHub 등 MCP 서버 |
| `config/*.yaml` | 비즈니스 설정 | 디자인 시스템, 조정 분류, NWC 정의 |

---

## 7. 문서 생성 라이브러리별 핵심 사용법과 제약사항

| 라이브러리 | 용도 | 핵심 포인트 | 제약사항 |
|---|---|---|---|
| **python-pptx** | PPT 생성 | 템플릿 기반 생성 권장, `Presentation('template.pptx')` | 워터폴 차트 미지원 → Plotly 이미지 삽입 |
| **openpyxl** | Excel 생성 | 수식/조건부서식/차트 모두 지원, Named Styles 활용 | 3.1.4 버전 차트 렌더링 버그 → 3.1.3 사용 권장 |
| **python-docx / docxtpl** | Word 생성 | docxtpl의 Jinja2 템플릿이 복잡한 보고서에 최적 | 차트 직접 생성 불가 → 이미지로 삽입 |
| **reportlab** | PDF 생성 | Platypus로 복잡한 레이아웃 가능 | 한글 폰트 별도 설정 필요 |
| **Plotly** | 차트 생성 | `go.Waterfall` 네이티브 지원, 300 DPI PNG export | `kaleido` 엔진 필요, 서버 환경 설정 주의 |
| **matplotlib** | 차트 생성 | 세밀한 커스터마이징 가능, BytesIO 인메모리 전달 | 워터폴 차트 직접 지원 없음, 수동 구현 필요 |

Anthropic 공식 PPTX 스킬은 새 프레젠테이션 생성 시 **html2pptx 워크플로우**(HTML → JavaScript → PPTX)를 사용하고, 기존 파일 편집 시 **OOXML 직접 편집**(unpack → XML 수정 → validate → repack)을 사용한다. XLSX 스킬은 openpyxl과 pandas를 조합하되, **모든 수치 계산은 반드시 Excel 수식으로 유지**하는 것이 철칙이다.

---

## 결론: FDD 자동화의 실현 가능 범위와 전략적 우선순위

Claude Code의 Skills + Agents + MCP 아키텍처는 FDD 보고서 생성 파이프라인의 **데이터 수집 → 정량 분석 → 차트 생성 → 보고서 조립** 전체를 커버한다. 자동화 적합도가 높은 영역부터 우선 구현하는 것이 현실적이다: EBITDA 계산·NWC 트렌딩·재무비율 산출은 **완전 자동화** 가능하고, 조정 항목 식별·리스크 플래깅은 **AI 보조 + 인간 검증** 방식이며, 전문가 판단이 필요한 조정 결정·경영진 인터뷰 분석은 **시스템이 기록하되 인간이 결정**하는 구조가 적절하다. 

프로젝트의 핵심 차별점은 YAML 설정 파일로 NWC 정의, 조정 분류 체계, 디자인 시스템을 **딜마다 교체 가능**하게 만드는 것이다. 모든 딜이 다르기 때문에, 분석 로직을 하드코딩하지 않고 설정 기반으로 유연하게 구성해야 실무에서 반복 사용할 수 있다.