# Claude Code 규칙·스킬·에이전트 완전 정복 가이드

**Claude Code는 규칙(Rules), 스킬(Skills), 에이전트(Agents)라는 세 가지 핵심 설정 체계를 통해 프로젝트에 최적화된 AI 코딩 어시스턴트로 변신합니다.** 이 세 체계를 제대로 설정하면, KIIS(차세대 지능형 투자정보 통합 시스템) 같은 복잡한 프로젝트도 초보자가 체계적으로 개발할 수 있습니다. 규칙은 "항상 지켜야 할 약속"이고, 스킬은 "필요할 때 꺼내 쓰는 전문 능력"이며, 에이전트는 "독립적으로 일하는 AI 팀원"입니다. 이 가이드는 2025~2026년 최신 정보를 기반으로, VS Code 환경에서 KIIS 프로젝트를 시작하는 완전 초보자를 위해 복사·붙여넣기 가능한 실전 코드와 함께 모든 설정법을 단계별로 설명합니다.

---

## 1단계: VS Code에서 Claude Code 설치하고 시작하기

Claude Code를 사용하려면 먼저 VS Code에 확장 프로그램을 설치해야 합니다. **VS Code 1.98.0 이상**이 필요하며, Anthropic 계정(Pro, Max, Team, Enterprise 중 하나) 또는 API 과금 계정이 있어야 합니다.

설치는 간단합니다. VS Code를 열고 `Ctrl+Shift+X`(Windows/Linux) 또는 `Cmd+Shift+X`(Mac)를 눌러 확장 마켓플레이스를 연 뒤, 검색창에 **"Claude Code"**를 입력하고 퍼블리셔가 **Anthropic**인 확장을 설치하면 됩니다. 설치 후 VS Code를 재시작하면 하단 상태 바에 **✱ Claude Code** 아이콘이 나타납니다. 이것을 클릭하면 로그인 화면이 뜨고, Anthropic 계정으로 OAuth 인증을 완료하면 바로 사용할 수 있습니다.

### VS Code 기본 설정 최적화

Claude Code를 편하게 쓰려면 VS Code의 `settings.json`에 아래 설정을 추가하세요. `Ctrl+Shift+P` → "Preferences: Open Settings (JSON)"을 선택하면 편집할 수 있습니다.

```json
{
  "claudeCode.preferredLocation": "sidebar",
  "claudeCode.initialPermissionMode": "normal",
  "terminal.integrated.fontSize": 14,
  "terminal.integrated.scrollback": 10000,
  "editor.formatOnSave": true,
  "files.autoSave": "afterDelay"
}
```

`claudeCode.preferredLocation`을 `"sidebar"`로 설정하면 Claude Code가 왼쪽 사이드바에 고정되어 코드를 보면서 대화할 수 있습니다. `"panel"`로 바꾸면 하단 패널에, `"editor"`로 바꾸면 에디터 탭으로 열립니다.

### 핵심 단축키 외우기

| 단축키 | 기능 |
|--------|------|
| `Cmd+Esc` / `Ctrl+Esc` | 에디터 ↔ Claude 패널 전환 |
| `Option+K` / `Alt+K` | 현재 선택한 코드를 Claude에 참조로 전달 |
| `Shift+Tab` | 권한 모드 순환 (일반 → 자동수락 → 플랜모드) |
| `Tab` | 확장 사고(Extended Thinking) 토글 |
| `/clear` | 대화 초기화 |
| `@파일명` | 특정 파일을 Claude에 참조로 전달 |

**플랜 모드**는 초보자에게 특히 유용합니다. Claude가 코드를 바로 수정하지 않고, 먼저 "이렇게 할 계획입니다"라는 계획서를 보여주고 승인을 기다립니다. `Shift+Tab`을 눌러 모드를 전환하면서 안전하게 작업할 수 있습니다.

---

## Claude Code 규칙(Rules) 시스템의 모든 것

규칙은 Claude Code에게 **"항상 이렇게 행동해라"**라고 알려주는 지침서입니다. 프로젝트의 코딩 스타일, 사용 기술, 금지 사항 등을 미리 정의해두면, 매번 반복 설명할 필요 없이 Claude가 일관된 코드를 생성합니다. 규칙 시스템은 크게 **메모리 파일(CLAUDE.md)**, **모듈형 규칙(.claude/rules/)**, **설정 파일(settings.json)** 세 가지로 구성됩니다.

### 메모리 파일(CLAUDE.md)은 프로젝트의 헌법이다

`CLAUDE.md`는 Claude Code의 가장 핵심적인 규칙 파일입니다. 프로젝트 루트에 이 파일을 만들면 Claude Code가 세션을 시작할 때마다 자동으로 읽어들입니다. 아래 표는 모든 메모리 파일의 종류와 우선순위입니다.

| 우선순위 | 파일 위치 | 공유 여부 | 용도 |
|---------|----------|----------|------|
| 1 (최상) | 엔터프라이즈 관리 정책 | 조직 전체 | IT 부서가 배포하는 조직 규칙 |
| 2 | `~/.claude/CLAUDE.md` | 개인 | 모든 프로젝트에 적용되는 개인 선호 |
| 3 | `./CLAUDE.md` 또는 `./.claude/CLAUDE.md` | Git 공유 | 팀이 공유하는 프로젝트 규칙 |
| 4 | `./CLAUDE.local.md` | 개인 (자동 gitignore) | 개인적 프로젝트 설정 |

**핵심 원리**: Claude Code는 현재 작업 디렉토리에서 시작해 상위 디렉토리까지 **재귀적으로 올라가며** 모든 `CLAUDE.md`를 찾아 읽습니다. 하위 디렉토리의 `CLAUDE.md`는 Claude가 해당 디렉토리의 파일을 작업할 때만 지연 로딩됩니다.

`CLAUDE.md` 작성 시 **150줄 이내**로 유지하는 것이 핵심입니다. Claude는 약 150~200개의 지시를 합리적으로 따를 수 있으며, 지시가 많아질수록 준수 품질이 균일하게 떨어집니다. 또한 `@경로` 구문으로 외부 파일을 임포트할 수 있습니다(최대 5단계 깊이).

### KIIS 프로젝트용 CLAUDE.md 실전 예시

아래는 KIIS 프로젝트에 바로 사용할 수 있는 `CLAUDE.md`입니다. 프로젝트 루트에 이 파일을 생성하세요.

```markdown
# KIIS 프로젝트 규칙

## 프로젝트 개요
KIIS(차세대 지능형 투자정보 통합 시스템)는 DART API, KOFIA 데이터, 뉴스 NLP 분석을 통합하는
Python 기반 투자정보 시스템이다.

## 기술 스택
- Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic
- PostgreSQL 16, Redis (캐싱)
- 데이터: pandas, numpy, konlpy (한국어 NLP)
- 테스트: pytest, pytest-asyncio
- 패키지 관리: uv (pip 대신 uv 사용)

## 코드 스타일
- 모든 함수와 클래스에 한국어 docstring 작성
- Type hints 필수 사용
- 변수명은 snake_case, 클래스명은 PascalCase
- 들여쓰기 4칸, 라인 최대 100자
- import 순서: 표준 라이브러리 → 서드파티 → 프로젝트 내부

## API 설계 규칙
- FastAPI 라우터는 기능별로 분리 (예: routers/dart.py, routers/news.py)
- 모든 API 엔드포인트에 Pydantic 스키마로 입출력 검증
- 에러 응답은 {"detail": "메시지", "code": "ERROR_CODE"} 형식 통일
- 비동기(async/await) 패턴 우선 사용

## 데이터베이스 규칙
- 마이그레이션은 반드시 Alembic으로 관리 (직접 SQL 수정 금지)
- 모든 테이블에 created_at, updated_at 컬럼 포함
- 인덱스는 쿼리 패턴에 맞게 설정하고 주석으로 이유 기록

## 보안 규칙
- IMPORTANT: .env 파일을 절대 Git에 커밋하지 않을 것
- API 키는 반드시 환경변수로 관리
- 사용자 입력은 항상 검증하고 SQL Injection 방지

## 테스트 규칙
- 새 기능은 반드시 테스트 코드와 함께 작성
- 테스트 실행: `uv run pytest tests/ -v`
- 린트 검사: `uv run ruff check .`

## 자주 쓰는 명령어
- 서버 실행: `uv run uvicorn app.main:app --reload --port 8000`
- DB 마이그레이션: `uv run alembic upgrade head`
- 새 마이그레이션: `uv run alembic revision --autogenerate -m "설명"`

## 참고 문서
- @docs/api-design.md 에서 API 설계 가이드라인 확인
- @docs/data-pipeline.md 에서 데이터 파이프라인 구조 확인
```

### 모듈형 규칙(.claude/rules/)으로 규칙을 분리 관리하기

프로젝트가 커지면 하나의 `CLAUDE.md`에 모든 규칙을 넣기 어려워집니다. **Claude Code v2.0.64**(2025년 12월)부터 `.claude/rules/` 디렉토리에 여러 마크다운 파일로 규칙을 분리할 수 있습니다. 이 디렉토리의 모든 `.md` 파일은 자동으로 로딩되며, `CLAUDE.md`와 동일한 높은 우선순위로 적용됩니다.

특히 강력한 기능은 **경로 기반 조건부 규칙**입니다. YAML 프론트매터로 `paths` 필드를 지정하면, 해당 경로의 파일을 작업할 때만 규칙이 활성화됩니다.

```markdown
---
paths:
  - "app/routers/**/*.py"
  - "app/api/**/*.py"
---

# FastAPI 라우터 규칙
- 모든 엔드포인트에 response_model 지정 필수
- 경로 파라미터에 Path(), 쿼리 파라미터에 Query() 사용
- Depends()로 의존성 주입 패턴 활용
- 각 라우터 파일 상단에 tags 정의
```

`paths` 필드가 없는 규칙 파일은 모든 상황에서 무조건 적용됩니다. glob 패턴은 반드시 따옴표로 감싸야 합니다.

### settings.json으로 권한과 환경을 제어하기

`.claude/settings.json`은 Claude Code의 도구 사용 권한, 환경변수, 훅(hook) 등을 제어합니다. 이 파일은 `CLAUDE.md`와 별개로, Claude가 **어떤 도구를 사용할 수 있는지**를 결정합니다.

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run pytest *)",
      "Bash(uv run ruff *)",
      "Bash(uv run uvicorn *)",
      "Bash(git status)",
      "Bash(git diff)",
      "Bash(git add *)",
      "Bash(git commit *)"
    ],
    "ask": [
      "Bash(git push *)",
      "Bash(uv pip install *)",
      "Bash(alembic *)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Bash(rm -rf *)"
    ]
  },
  "env": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```

**권한 평가 순서**는 deny → allow → ask입니다. 먼저 거부 규칙을 확인하고, 그다음 허용, 마지막으로 확인 요청 규칙을 적용합니다.

---

## Claude Code 스킬(Skills)은 필요할 때 꺼내 쓰는 전문 능력이다

스킬은 규칙과 근본적으로 다릅니다. **규칙은 항상 로딩되어 매 대화에 적용**되지만, **스킬은 Claude가 작업 맥락을 파악한 뒤 필요하다고 판단할 때만 자동으로 활성화**됩니다. 이것은 마치 전문가가 도구 상자에서 적절한 도구를 꺼내 쓰는 것과 같습니다. 덕분에 컨텍스트 윈도우를 효율적으로 사용할 수 있습니다.

스킬은 `.claude/skills/스킬이름/SKILL.md` 형식으로 정의합니다. Claude Code는 모든 스킬의 `name`과 `description`만 먼저 스캔(스킬당 약 100토큰)하고, 실제로 필요할 때만 전체 내용을 로딩하는 **점진적 공개(Progressive Disclosure)** 방식을 사용합니다.

### 스킬 생성 방법과 파일 구조

스킬을 만들려면 `.claude/skills/` 아래에 디렉토리를 생성하고, 그 안에 `SKILL.md` 파일을 작성합니다.

```
.claude/skills/
├── dart-api/
│   └── SKILL.md
├── news-crawler/
│   ├── SKILL.md
│   └── scripts/
│       └── parse_news.py
└── data-analysis/
    ├── SKILL.md
    └── reference.md
```

`SKILL.md`에는 YAML 프론트매터와 마크다운 본문을 씁니다. `name`은 소문자, 숫자, 하이픈만 사용(최대 64자), `description`은 최대 1024자로 Claude가 이 스킬을 언제 사용할지 판단하는 핵심 텍스트입니다.

### KIIS 프로젝트용 스킬 예시들

**스킬 1: DART API 연동** (`.claude/skills/dart-api/SKILL.md`)

```markdown
---
name: dart-api
description: DART(전자공시시스템) Open API 연동 코드를 작성합니다. 기업 재무제표, 공시 정보, 기업 개황 등을 조회하는 코드가 필요할 때 사용합니다. DART, 공시, 재무제표, 사업보고서 관련 작업에 활성화됩니다.
allowed-tools: Read, Grep, Glob, Bash
---

# DART API 연동 가이드

## 기본 설정
- DART API 키는 환경변수 `DART_API_KEY`에서 로드
- Base URL: https://opendart.fss.or.kr/api/
- 모든 요청에 httpx 비동기 클라이언트 사용

## 주요 엔드포인트
1. 공시검색: `/list.json` (corp_code, bgn_de, end_de, page_no, page_count)
2. 기업개황: `/company.json` (corp_code)
3. 단일회사 전체 재무제표: `/fnlttSinglAcntAll.json`
4. 고유번호 조회: `/corpCode.xml` (ZIP 파일로 반환)

## 코드 패턴
```python
import httpx
from app.core.config import settings

async def fetch_dart_data(endpoint: str, params: dict) -> dict:
    """DART API에서 데이터를 비동기로 가져옵니다."""
    async with httpx.AsyncClient() as client:
        params["crtfc_key"] = settings.DART_API_KEY
        response = await client.get(
            f"https://opendart.fss.or.kr/api/{endpoint}",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
```

## 에러 처리
- status "000": 정상, "010": 등록되지 않은 키
- 요청 제한: 분당 1000회, 일 10000회
- 반드시 rate limiting 구현할 것
```

**스킬 2: 뉴스 NLP 분석** (`.claude/skills/news-nlp/SKILL.md`)

```markdown
---
name: news-nlp
description: 한국어 금융 뉴스 크롤링 및 NLP 감성분석 코드를 작성합니다. 뉴스 수집, 텍스트 분석, 감성분석, 키워드 추출 작업에 사용됩니다.
allowed-tools: Read, Grep, Glob, Bash
---

# 뉴스 NLP 분석 가이드

## 크롤링 규칙
- robots.txt 준수 필수
- 요청 간격 최소 2초 유지 (asyncio.sleep)
- User-Agent 헤더 필수 설정
- BeautifulSoup4 + httpx 조합 사용

## 한국어 NLP 파이프라인
1. 형태소 분석: konlpy의 Okt 사용
2. 불용어 제거: app/data/stopwords_ko.txt 참조
3. 감성분석: 금융 도메인 감성 사전 활용
4. 키워드 추출: TF-IDF 기반

## 코드 패턴
```python
from konlpy.tag import Okt
from collections import Counter

okt = Okt()

def extract_keywords(text: str, top_n: int = 10) -> list[tuple[str, int]]:
    """한국어 텍스트에서 주요 키워드를 추출합니다."""
    nouns = okt.nouns(text)
    filtered = [n for n in nouns if len(n) > 1]
    return Counter(filtered).most_common(top_n)
```
```

**스킬 3: 데이터베이스 작업** (`.claude/skills/database-ops/SKILL.md`)

```markdown
---
name: database-ops
description: PostgreSQL 데이터베이스 스키마 설계, SQLAlchemy 모델 작성, Alembic 마이그레이션 관련 코드를 작성합니다. DB, 테이블, 모델, 마이그레이션 작업에 사용됩니다.
allowed-tools: Read, Grep, Glob, Bash
---

# 데이터베이스 작업 가이드

## SQLAlchemy 모델 패턴
```python
from sqlalchemy import Column, Integer, String, DateTime, func
from app.database.base import Base

class CompanyInfo(Base):
    """기업 기본 정보 테이블"""
    __tablename__ = "company_info"

    id = Column(Integer, primary_key=True, index=True)
    corp_code = Column(String(8), unique=True, nullable=False, comment="DART 고유번호")
    corp_name = Column(String(100), nullable=False, comment="회사명")
    stock_code = Column(String(6), nullable=True, comment="종목코드")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

## 마이그레이션 명령어
- 새 마이그레이션: `uv run alembic revision --autogenerate -m "설명"`
- 적용: `uv run alembic upgrade head`
- 롤백: `uv run alembic downgrade -1`
- IMPORTANT: migrations 폴더를 직접 수정하지 말 것
```

### 스킬 vs 규칙 vs 명령어 핵심 비교

| 특성 | 규칙 (CLAUDE.md / rules/) | 스킬 (.claude/skills/) | 명령어 (.claude/commands/) |
|------|--------------------------|----------------------|--------------------------|
| **누가 작동시키나** | 항상 자동 로딩 | Claude가 필요시 자동 활성화 | 사용자가 `/명령어`로 직접 실행 |
| **컨텍스트 비용** | 항상 소비 | 필요할 때만 소비 | 실행할 때만 소비 |
| **적합한 용도** | 코딩 컨벤션, 보안 규칙 | 특정 작업 워크플로우 | 반복적인 수동 작업 |
| **스크립트 포함** | 불가 | 가능 | 불가 |

실용적 판단 기준은 이렇습니다. "`.env` 파일을 절대 커밋하지 마라"처럼 **항상 적용되어야 하는 것**은 규칙으로, "DART API 코드를 작성할 때 이 패턴을 따라라"처럼 **특정 작업에만 필요한 것**은 스킬로, "프로덕션 배포"처럼 **사용자가 의도적으로 실행해야 하는 것**은 `disable-model-invocation: true` 설정한 스킬로 만듭니다.

---

## Claude Code 에이전트(Agents)는 독립적으로 일하는 AI 팀원이다

Claude Code는 본질적으로 **에이전트**입니다. 도구에 접근하고, 자율적으로 판단하며, 작업이 완료될 때까지 반복합니다. 하지만 더 강력한 기능은 **서브에이전트(Sub-agent)**를 생성하여 복잡한 작업을 분할·병렬 처리하는 것입니다.

### Task 도구로 서브에이전트 생성하기

Claude Code의 **Task 도구**가 서브에이전트의 핵심 메커니즘입니다. Claude가 복잡한 작업을 받으면 스스로 Task 도구를 호출하여 독립적인 Claude 인스턴스를 생성합니다. 각 서브에이전트는 **자체 컨텍스트 윈도우**에서 실행되므로 메인 대화의 컨텍스트를 소비하지 않습니다. **최대 7개**의 서브에이전트가 동시에 병렬 실행될 수 있습니다. 단, 서브에이전트는 또 다른 서브에이전트를 생성할 수 없습니다(1단계 깊이 제한).

### 내장 서브에이전트 타입

Claude Code에는 세 가지 내장 서브에이전트 타입이 있습니다. **Explore 에이전트**는 Haiku 모델을 사용하며 읽기 전용으로 파일 탐색과 코드 검색에 최적화되어 있습니다. **General-purpose 에이전트**는 Sonnet 모델로 읽기·쓰기·실행 모든 도구를 사용할 수 있어 복잡한 작업에 적합합니다. **Plan 에이전트**는 플랜 모드에서 코드베이스를 조사하며 계획을 수립합니다.

### 커스텀 서브에이전트 만들기

`.claude/agents/` 디렉토리에 마크다운 파일을 생성하면 커스텀 에이전트를 정의할 수 있습니다. 또는 Claude Code 내에서 `/agents` 명령어로 대화형 인터페이스를 통해 생성할 수도 있습니다.

**KIIS 프로젝트용 커스텀 에이전트 예시들:**

**에이전트 1: 데이터 수집 전문가** (`.claude/agents/data-collector.md`)

```markdown
---
name: data-collector
description: DART API, KOFIA 웹사이트, 뉴스 사이트에서 데이터를 수집하는 전문 에이전트. 데이터 파이프라인 구축, 크롤러 작성, API 연동 코드가 필요할 때 자동으로 호출됩니다.
tools: Read, Grep, Glob, Bash, Edit, Write
model: sonnet
skills: dart-api, news-crawler
---

당신은 KIIS 프로젝트의 데이터 수집 전문가입니다.

## 전문 분야
1. DART Open API를 통한 기업 공시/재무 데이터 수집
2. KOFIA(금융투자협회) 웹사이트 크롤링
3. 금융 뉴스 사이트 크롤링 (robots.txt 준수)
4. 데이터 수집 파이프라인 설계 및 스케줄링

## 작업 원칙
- 모든 HTTP 요청은 httpx 비동기 클라이언트 사용
- rate limiting을 반드시 구현
- 수집한 데이터는 반드시 유효성 검증 후 저장
- 에러 발생 시 재시도 로직 구현 (exponential backoff)
- 크롤링 시 robots.txt와 이용약관 준수
```

**에이전트 2: 코드 리뷰어** (`.claude/agents/code-reviewer.md`)

```markdown
---
name: code-reviewer
description: 코드 변경사항을 리뷰하고 품질을 점검하는 에이전트. 코드 리뷰, 품질 검사, 보안 점검이 필요할 때 사용됩니다.
tools: Read, Grep, Glob
model: haiku
---

당신은 KIIS 프로젝트의 시니어 코드 리뷰어입니다.

## 리뷰 체크리스트
1. Type hints가 모든 함수에 적용되었는지 확인
2. docstring이 한국어로 작성되었는지 확인
3. SQL Injection 등 보안 취약점 점검
4. 에러 처리가 적절한지 확인
5. 테스트 코드가 함께 작성되었는지 확인
6. .env 파일이나 API 키가 하드코딩되지 않았는지 확인

## 출력 형식
각 발견 사항을 [심각도: 높음/중간/낮음] 형태로 보고하세요.
```

### 에이전트 팀(Agent Teams)으로 대규모 병렬 작업 수행하기

2026년 2월 도입된 **에이전트 팀**은 여러 Claude 인스턴스가 서로 직접 메시지를 교환하며 협업하는 멀티에이전트 시스템입니다. 서브에이전트와 달리, 팀원들은 **피어-투-피어 통신**이 가능하고 공유 태스크 리스트로 작업을 조율합니다.

활성화하려면 `~/.claude/settings.json`에 아래를 추가합니다.

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

에이전트 팀은 **팀 리더**(메인 세션)가 팀을 생성하고, **팀원**들에게 작업을 배분하며, 결과를 종합하는 구조입니다. KIIS 프로젝트에서의 활용 예시로는, 팀 리더가 "DART 데이터 수집", "뉴스 크롤링", "NLP 감성분석", "API 엔드포인트 구현"을 각각 다른 팀원에게 동시에 맡기고, 완료 후 통합하는 패턴이 가능합니다. 다만 각 팀원이 완전한 Claude 인스턴스이므로 **토큰 비용이 약 5배** 증가한다는 점에 주의해야 합니다.

### 서브에이전트 vs 에이전트 팀 선택 기준

| 특성 | 서브에이전트 | 에이전트 팀 |
|------|------------|------------|
| 컨텍스트 | 결과만 부모에게 반환 | 각자 독립 컨텍스트 |
| 통신 | 부모에게만 보고 | 팀원 간 직접 메시지 가능 |
| 비용 | 중간 | 높음 (팀원당 ~5배) |
| 적합한 상황 | 빠른 집중 작업 | 장기적이고 복잡한 병렬 작업 |

초보자에게는 **서브에이전트만으로 충분**합니다. Claude Code에게 복잡한 작업을 지시하면 스스로 서브에이전트를 적절히 생성하므로, 별도 설정 없이도 자동으로 멀티에이전트의 혜택을 받을 수 있습니다.

---

## KIIS 프로젝트 전체 폴더 구조와 단계별 설정 가이드

이제 모든 지식을 종합하여, KIIS 프로젝트를 처음부터 구축하는 전체 과정을 단계별로 안내합니다.

### 전체 폴더 구조

```
kiis-project/
├── CLAUDE.md                          # 프로젝트 핵심 규칙
├── CLAUDE.local.md                    # 개인 설정 (자동 gitignore)
├── .mcp.json                          # MCP 서버 설정
├── .gitignore
├── .env.example                       # 환경변수 템플릿
├── pyproject.toml                     # Python 프로젝트 설정
├── alembic.ini                        # Alembic 설정
│
├── .vscode/
│   └── settings.json                  # VS Code 프로젝트 설정
│
├── .claude/
│   ├── settings.json                  # Claude Code 프로젝트 설정
│   ├── settings.local.json            # 개인 Claude 설정 (gitignore)
│   │
│   ├── rules/                         # 모듈형 규칙
│   │   ├── api-design.md              # API 설계 규칙
│   │   ├── database.md                # DB 규칙
│   │   ├── testing.md                 # 테스트 규칙
│   │   └── security.md               # 보안 규칙
│   │
│   ├── skills/                        # 스킬 (필요시 자동 활성화)
│   │   ├── dart-api/
│   │   │   └── SKILL.md
│   │   ├── news-nlp/
│   │   │   └── SKILL.md
│   │   ├── database-ops/
│   │   │   └── SKILL.md
│   │   └── kofia-crawler/
│   │       └── SKILL.md
│   │
│   └── agents/                        # 커스텀 에이전트
│       ├── data-collector.md
│       └── code-reviewer.md
│
├── app/                               # 메인 애플리케이션
│   ├── __init__.py
│   ├── main.py                        # FastAPI 앱 진입점
│   ├── core/
│   │   ├── config.py                  # 설정 관리
│   │   └── database.py                # DB 연결
│   ├── models/                        # SQLAlchemy 모델
│   │   ├── company.py
│   │   └── financial.py
│   ├── schemas/                       # Pydantic 스키마
│   │   ├── company.py
│   │   └── financial.py
│   ├── routers/                       # API 라우터
│   │   ├── dart.py
│   │   ├── news.py
│   │   └── analysis.py
│   ├── services/                      # 비즈니스 로직
│   │   ├── dart_service.py
│   │   ├── news_service.py
│   │   └── nlp_service.py
│   └── utils/                         # 유틸리티
│       ├── http_client.py
│       └── rate_limiter.py
│
├── migrations/                        # Alembic 마이그레이션
│   └── versions/
│
├── tests/                             # 테스트 코드
│   ├── conftest.py
│   ├── test_dart_service.py
│   └── test_news_service.py
│
└── docs/                              # 프로젝트 문서
    ├── api-design.md
    └── data-pipeline.md
```

### 단계별 설정 가이드

**1단계: 프로젝트 디렉토리 생성**

VS Code에서 터미널을 열고(`Ctrl+~`) 다음 명령어를 실행합니다.

```bash
mkdir kiis-project
cd kiis-project
git init
```

**2단계: Claude Code에게 기본 구조 생성 요청**

VS Code에서 Claude Code 패널을 열고(사이드바 아이콘 클릭) 다음과 같이 입력합니다.

```
이 프로젝트의 기본 폴더 구조를 만들어줘. Python 3.11, FastAPI, SQLAlchemy, PostgreSQL 기반의
투자정보 시스템이야. .claude/ 디렉토리에 rules, skills, agents 폴더도 함께 만들어줘.
pyproject.toml도 uv를 사용하는 형태로 만들어줘.
```

**3단계: CLAUDE.md 생성**

프로젝트 루트에 `CLAUDE.md` 파일을 만들고, 위에서 제공한 KIIS 프로젝트용 CLAUDE.md 내용을 붙여넣습니다.

**4단계: .claude/settings.json 생성**

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run pytest *)",
      "Bash(uv run ruff *)",
      "Bash(uv run uvicorn *)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(cat *)",
      "Bash(ls *)",
      "Bash(find *)"
    ],
    "ask": [
      "Bash(git push *)",
      "Bash(uv add *)",
      "Bash(alembic *)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Bash(rm -rf *)"
    ]
  }
}
```

**5단계: 모듈형 규칙 파일 생성**

`.claude/rules/security.md` 파일을 생성합니다.

```markdown
# 보안 규칙

- API 키, 비밀번호, 토큰 등 민감 정보는 절대 코드에 하드코딩하지 않는다
- 환경변수는 pydantic-settings의 BaseSettings로 관리한다
- 사용자 입력은 반드시 Pydantic 모델로 검증한다
- SQL 쿼리에 문자열 포매팅(f-string)을 직접 사용하지 않는다
- CORS 설정은 허용된 도메인만 명시적으로 지정한다
```

`.claude/rules/testing.md` 파일을 생성합니다.

```markdown
# 테스트 규칙

- 새 기능에는 반드시 단위 테스트를 함께 작성한다
- 테스트 파일명은 test_로 시작한다
- 비동기 테스트에는 pytest-asyncio와 @pytest.mark.asyncio 데코레이터를 사용한다
- 외부 API 호출은 pytest-httpx 또는 unittest.mock으로 모킹한다
- 픽스처는 tests/conftest.py에 정의한다
```

**6단계: 스킬 파일 생성**

위에서 제공한 `dart-api`, `news-nlp`, `database-ops` 스킬 파일을 각각 해당 디렉토리에 생성합니다.

KOFIA 크롤러 스킬도 추가합니다 (`.claude/skills/kofia-crawler/SKILL.md`).

```markdown
---
name: kofia-crawler
description: KOFIA(한국금융투자협회) 웹사이트에서 펀드 정보, 채권 데이터를 크롤링하는 코드를 작성합니다. KOFIA, 펀드, 채권, 금융투자협회 관련 작업에 사용됩니다.
allowed-tools: Read, Grep, Glob, Bash
---

# KOFIA 크롤링 가이드

## 크롤링 대상
- 펀드 공시: https://dis.kofia.or.kr
- 채권 시가평가: https://www.kofiabond.or.kr

## 기술 스택
- httpx + BeautifulSoup4 조합
- 동적 페이지는 playwright 사용 고려

## 핵심 원칙
- robots.txt 반드시 확인하고 준수
- 요청 간격 3초 이상 유지
- 세션 관리가 필요한 경우 httpx.AsyncClient의 cookies 활용
- 수집 데이터는 즉시 Pydantic 모델로 검증
```

**7단계: 에이전트 파일 생성**

위에서 제공한 `data-collector.md`와 `code-reviewer.md`를 `.claude/agents/` 디렉토리에 생성합니다.

**8단계: .gitignore 설정**

```
# 환경
.env
.env.*
!.env.example

# Python
__pycache__/
*.pyc
.venv/

# Claude Code 개인 파일 (자동으로도 추가되지만 명시)
CLAUDE.local.md
.claude/settings.local.json
.claude/CLAUDE.local.md

# IDE
.vscode/settings.json
.idea/
```

**9단계: 개발 시작하기**

모든 설정이 끝나면 Claude Code 패널에서 이렇게 대화를 시작합니다.

```
KIIS 프로젝트의 첫 번째 기능으로 DART API에서 기업 재무제표를 수집하는
서비스를 만들어줘. app/services/dart_service.py에 비동기 함수로 작성하고,
테스트 코드도 함께 만들어줘.
```

Claude Code는 `CLAUDE.md`의 규칙을 따르고, DART 관련 작업이므로 `dart-api` 스킬을 자동으로 활성화하며, 필요하면 `data-collector` 에이전트 패턴으로 서브에이전트를 생성하여 작업을 수행합니다.

---

## MCP로 Claude Code의 능력을 확장하기

MCP(Model Context Protocol)는 Claude Code를 외부 도구와 연결하는 표준 프로토콜입니다. 프로젝트 루트에 `.mcp.json` 파일을 생성하면 됩니다. 스킬이 "어떻게 할지"를 가르친다면, MCP는 "어디에 접근할지"를 연결합니다.

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/kiis"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./docs"]
    }
  }
}
```

이렇게 설정하면 Claude Code가 PostgreSQL 데이터베이스에 직접 쿼리하거나, 지정된 디렉토리의 파일을 탐색할 수 있습니다. `/mcp` 명령어로 설정된 MCP 서버를 관리할 수 있습니다.

---

## 초보자가 반드시 기억해야 할 핵심 원칙

Claude Code의 규칙·스킬·에이전트 시스템은 처음에 복잡해 보이지만, 핵심 원칙은 단순합니다.

**CLAUDE.md는 150줄 이내로 유지**하세요. 지시가 많아질수록 Claude의 준수율이 떨어집니다. 핵심만 넣고, 상세 규칙은 `.claude/rules/`에 분리하세요. **스킬은 "설명(description)"이 생명**입니다. Claude가 스킬을 자동 활성화할지 결정하는 유일한 기준이 description이므로, 구체적인 키워드와 사용 시나리오를 명확히 적어야 합니다. **에이전트는 처음부터 만들 필요 없습니다**. Claude Code가 자체적으로 서브에이전트를 생성하므로, 프로젝트가 성숙한 뒤에 반복 패턴이 보일 때 커스텀 에이전트를 정의하면 됩니다.

가장 실용적인 시작 방법은 `CLAUDE.md` 하나만 먼저 만들고, 점차 규칙 파일을 분리하고, 스킬을 추가하고, 필요할 때 에이전트를 정의하는 **점진적 확장** 전략입니다. 처음부터 모든 설정을 완벽하게 갖출 필요는 없습니다. Claude Code를 사용하면서 `#` 단축키로 새로운 규칙을 즉시 추가하고, `/memory` 명령어로 기존 규칙을 수정하는 **반복적 개선**이 가장 효과적인 접근법입니다.