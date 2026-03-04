"""TemplateExtractor — 참조 보고서에서 YAML 템플릿 초안 자동 생성.

> 마지막 수정: 2026-02-17

참조 IM 보고서(PDF 또는 PPTX)의 텍스트를 분석하여,
부동문자(L1) + 슬롯 마커(L2/L3) + 조건부 블록(L4) 구조의
YAML 템플릿 초안을 생성한다.

LLM을 활용하여 고정 텍스트(부동문자)와 가변 텍스트(슬롯)를
자동으로 분류한다.

파이프라인:
  1. 텍스트 추출: PDF(pymupdf) 또는 PPTX(python-pptx)에서 원문 추출
  2. 섹션 분할: 보고서를 논리적 섹션으로 분할
  3. LLM 분석: 고정/가변 텍스트 분류 및 슬롯 정의 생성
  4. YAML 생성: SectionTemplate 구조에 맞는 YAML 파일 출력

사용 예시::

    extractor = TemplateExtractor(llm_client=openai_client)
    result = await extractor.extract_from_file(
        file_path="reference_im.pdf",
        section_id="executive_summary",
    )
    result.save_yaml("templates/executive_summary.yaml")
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# ── 섹션 식별 패턴 ──
_SECTION_PATTERNS: dict[str, list[str]] = {
    "executive_summary": ["executive summary", "경영진 요약", "요약", "개요"],
    "company_overview": ["company overview", "회사 개요", "기업 개요", "회사 소개"],
    "business_overview": ["business overview", "사업 개요", "사업 현황"],
    "deal_overview": [
        "deal overview",
        "거래 개요",
        "거래 구조",
        "transaction overview",
    ],
    "financial_analysis": [
        "financial analysis",
        "재무 분석",
        "재무 현황",
        "financial overview",
    ],
    "investment_highlights": ["investment highlights", "투자 하이라이트", "투자 매력"],
    "market_overview": [
        "market overview",
        "시장 분석",
        "시장 개요",
        "industry overview",
    ],
    "value_creation": ["value creation", "가치 창출", "value-add"],
    "growth_strategy": ["growth strategy", "성장 전략", "strategic plan"],
    "management_team": ["management team", "경영진", "key personnel"],
    "business_model": ["business model", "비즈니스 모델", "수익 구조"],
    "appendix": ["appendix", "부록", "참고 자료"],
    "contact": ["contact", "연락처", "담당자"],
}

# ── LLM 프롬프트 ──
_EXTRACTION_SYSTEM_PROMPT = """\
## 역할
당신은 Investment Memorandum(IM) 보고서를 분석하여 부동문자 템플릿으로 변환하는 전문가입니다.

## 작업
주어진 IM 보고서 텍스트에서:
1. **부동문자(Boilerplate)**: 매번 동일하게 반복되는 고정 텍스트를 식별합니다.
2. **슬롯(Variable)**: 기업/거래마다 달라지는 가변 텍스트를 식별하고 슬롯으로 마킹합니다.

## 슬롯 레벨 분류
- **L1**: 완전 고정 텍스트 (면책조항, "본 자료는..." 등) — 그대로 유지
- **L2**: 단순 데이터 치환 (기업명, 날짜, 금액 등) — `{{slot_name}}` + source 지정
- **L3**: LLM이 생성해야 하는 분석/설명 텍스트 — `{{slot_name}}` + hint/data_keys 지정
- **L4**: 산업/조건에 따라 삽입되는 조건부 블록

## 응답 형식
반드시 다음 JSON 구조로만 응답하십시오:

```json
{
  "section_id": "섹션 식별자",
  "slots": {
    "slot_name": {
      "level": "L2 또는 L3",
      "source": "L2일 때 IMDocumentData 필드 경로",
      "type": "sentence | paragraph | bullet_list | number",
      "hint": "L3일 때 LLM 작성 가이드",
      "max_tokens": 80,
      "data_keys": ["관련 데이터 경로"]
    }
  },
  "body": "부동문자 + {{slot_name}} 마커가 포함된 본문",
  "conditional_blocks": [
    {
      "condition": "industry == 'tech'",
      "insert_after": "슬롯명",
      "text": "조건부 삽입 텍스트"
    }
  ]
}
```

## 슬롯 이름 규칙
- snake_case 사용 (예: company_intro, revenue_highlight)
- 의미를 명확히 반영 (예: market_opportunity, ebitda_comment)

## IMDocumentData 주요 필드 경로 (L2 source용)
- company_name_kr, company_name_en
- date, project_name
- deal_structure.transaction_type
- financial_statements.revenue, financial_statements.ebitda
- market_data.tam, market_data.market_growth_rate
- company_overview.business_model, company_overview.established_date
- derived_metrics (CAGR, 마진 등)
- contacts.0.name, contacts.0.title, contacts.0.email

## 주의사항
- 수치가 포함된 문장은 대부분 L3 슬롯입니다 (매번 달라지므로).
- 기업명, 날짜, 거래유형 등 단순 대입 가능한 것만 L2로 지정하십시오.
- 면책조항, 비밀유지 등 법적 문구는 L1(body에 고정 텍스트)로 유지하십시오.
- 한국어 부동문자의 자연스러운 흐름을 유지하십시오.
"""

_EXTRACTION_USER_TEMPLATE = """\
## 분석 대상 섹션: {section_id}

## 원문 텍스트
{text}

## 요청
위 텍스트를 부동문자 템플릿으로 변환하십시오.
- 고정 텍스트는 body에 그대로 유지
- 가변 텍스트는 {{slot_name}}으로 대체하고 slots에 정의
- 기업명/날짜 등 단순 대입 → L2
- 분석/설명 텍스트 → L3
- 산업별 특화 내용이 있으면 conditional_blocks로 분리

JSON으로만 응답하십시오.
"""

_SECTION_SPLIT_SYSTEM_PROMPT = """\
## 역할
당신은 IM(Investment Memorandum) 보고서의 섹션 구조를 분석하는 전문가입니다.

## 작업
주어진 보고서 텍스트를 논리적 섹션으로 분할하십시오.

## 응답 형식
반드시 다음 JSON 배열로만 응답하십시오:

```json
[
  {
    "section_id": "executive_summary",
    "title": "섹션 제목",
    "start_marker": "섹션 시작 텍스트 (첫 20자)",
    "text": "섹션 전체 텍스트"
  }
]
```

## 사용 가능한 section_id
executive_summary, company_overview, business_overview, deal_overview,
financial_analysis, investment_highlights, market_overview, value_creation,
growth_strategy, management_team, business_model, appendix, contact
"""


@dataclass
class ExtractionResult:
    """템플릿 추출 결과.

    Attributes:
        section_id: 섹션 식별자.
        yaml_content: 생성된 YAML 문자열.
        raw_response: LLM 원본 응답.
        source_file: 원본 파일 경로.
        warnings: 추출 중 발생한 경고.
    """

    section_id: str
    yaml_content: str
    raw_response: str = ""
    source_file: str = ""
    warnings: list[str] = field(default_factory=list)

    def save_yaml(self, output_path: str | Path) -> Path:
        """YAML 파일을 저장한다.

        Args:
            output_path: 저장 경로.

        Returns:
            저장된 파일의 Path.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.yaml_content, encoding="utf-8")
        logger.info("YAML 템플릿 저장: %s", path)
        return path


@dataclass
class SectionChunk:
    """분할된 섹션 텍스트.

    Attributes:
        section_id: 추정된 섹션 식별자.
        title: 섹션 제목.
        text: 섹션 텍스트.
    """

    section_id: str
    title: str
    text: str


class TemplateExtractor:
    """참조 보고서에서 YAML 템플릿 초안을 자동 생성한다.

    PDF 또는 PPTX 파일을 읽고, LLM을 활용하여 부동문자(L1)와
    슬롯(L2/L3/L4)을 분류한 뒤, YAML 템플릿 초안을 생성한다.

    Args:
        llm_client: OpenAI 클라이언트 인스턴스.
        model: 사용할 LLM 모델명.
        temperature: LLM 응답 온도.

    Usage:
        from openai import OpenAI
        client = OpenAI()
        extractor = TemplateExtractor(llm_client=client)

        # 단일 섹션 추출
        result = await extractor.extract_from_file(
            "reference.pdf", section_id="executive_summary",
        )
        result.save_yaml("templates/executive_summary.yaml")

        # 전체 보고서 자동 분할 + 추출
        results = await extractor.extract_all_sections("reference.pdf")
        for r in results:
            r.save_yaml(f"templates/{r.section_id}.yaml")
    """

    def __init__(
        self,
        llm_client: Any = None,
        *,
        model: str = "gpt-4o",
        temperature: float = 0.1,
    ) -> None:
        self._client = llm_client
        self._model = model
        self._temperature = temperature

    async def extract_from_file(
        self,
        file_path: str | Path,
        *,
        section_id: str = "",
        section_text: str = "",
    ) -> ExtractionResult:
        """파일에서 단일 섹션의 YAML 템플릿을 추출한다.

        Args:
            file_path: PDF 또는 PPTX 파일 경로.
            section_id: 추출할 섹션 ID (비어 있으면 자동 감지).
            section_text: 이미 추출된 텍스트 (비어 있으면 파일에서 추출).

        Returns:
            ExtractionResult.
        """
        file_path = Path(file_path)

        if not section_text:
            full_text = self._extract_text(file_path)
            if not full_text:
                return ExtractionResult(
                    section_id=section_id or "unknown",
                    yaml_content="",
                    warnings=["텍스트 추출 실패"],
                    source_file=str(file_path),
                )
            section_text = full_text

        if not section_id:
            section_id = self._guess_section_id(section_text)

        raw_response = await self._analyze_with_llm(section_text, section_id)
        parsed = self._parse_llm_response(raw_response)

        warnings: list[str] = []
        if not parsed:
            warnings.append("LLM 응답 파싱 실패, 원본 응답을 YAML 주석으로 포함")
            yaml_content = self._build_fallback_yaml(
                section_id,
                section_text,
                raw_response,
            )
        else:
            yaml_content = self._build_yaml(parsed, section_id, str(file_path))

        return ExtractionResult(
            section_id=section_id,
            yaml_content=yaml_content,
            raw_response=raw_response,
            source_file=str(file_path),
            warnings=warnings,
        )

    async def extract_all_sections(
        self,
        file_path: str | Path,
    ) -> list[ExtractionResult]:
        """파일에서 모든 섹션의 YAML 템플릿을 추출한다.

        보고서를 자동으로 섹션별로 분할한 뒤, 각 섹션의 템플릿을 생성한다.

        Args:
            file_path: PDF 또는 PPTX 파일 경로.

        Returns:
            ExtractionResult 리스트.
        """
        file_path = Path(file_path)
        full_text = self._extract_text(file_path)
        if not full_text:
            return [
                ExtractionResult(
                    section_id="unknown",
                    yaml_content="",
                    warnings=["텍스트 추출 실패"],
                    source_file=str(file_path),
                )
            ]

        chunks = await self._split_sections(full_text)
        if not chunks:
            chunks = self._split_sections_heuristic(full_text)

        results: list[ExtractionResult] = []
        for chunk in chunks:
            result = await self.extract_from_file(
                file_path,
                section_id=chunk.section_id,
                section_text=chunk.text,
            )
            results.append(result)

        return results

    # -------------------------------------------------------------------
    # 텍스트 추출
    # -------------------------------------------------------------------

    def _extract_text(self, file_path: Path) -> str:
        """PDF 또는 PPTX에서 텍스트를 추출한다."""
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf(file_path)
        if suffix in (".pptx", ".ppt"):
            return self._extract_pptx(file_path)
        if suffix == ".txt":
            return file_path.read_text(encoding="utf-8")

        logger.error("지원하지 않는 파일 형식: %s", suffix)
        return ""

    @staticmethod
    def _extract_pdf(file_path: Path) -> str:
        """PyMuPDF로 PDF 텍스트를 추출한다."""
        try:
            import fitz  # pymupdf
        except ImportError:
            logger.error("pymupdf 미설치: pip install pymupdf")
            return ""

        try:
            doc = fitz.open(str(file_path))
            pages: list[str] = []
            for page in doc:
                pages.append(page.get_text())
            doc.close()
            return "\n\n".join(pages)
        except Exception as exc:
            logger.error("PDF 텍스트 추출 실패: %s — %s", file_path, exc)
            return ""

    @staticmethod
    def _extract_pptx(file_path: Path) -> str:
        """python-pptx로 PPTX 텍스트를 추출한다."""
        try:
            from pptx import Presentation
        except ImportError:
            logger.error("python-pptx 미설치: pip install python-pptx")
            return ""

        try:
            prs = Presentation(str(file_path))
            slides: list[str] = []
            for slide in prs.slides:
                texts: list[str] = []
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for paragraph in shape.text_frame.paragraphs:
                            text = paragraph.text.strip()
                            if text:
                                texts.append(text)
                    if shape.has_table:
                        table = shape.table
                        for row in table.rows:
                            row_texts = [cell.text.strip() for cell in row.cells]
                            texts.append(" | ".join(row_texts))
                if texts:
                    slides.append("\n".join(texts))
            return "\n\n---\n\n".join(slides)
        except Exception as exc:
            logger.error("PPTX 텍스트 추출 실패: %s — %s", file_path, exc)
            return ""

    # -------------------------------------------------------------------
    # 섹션 분할
    # -------------------------------------------------------------------

    async def _split_sections(self, text: str) -> list[SectionChunk]:
        """LLM을 사용하여 텍스트를 섹션별로 분할한다."""
        if not self._client:
            return []

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                messages=[
                    {"role": "system", "content": _SECTION_SPLIT_SYSTEM_PROMPT},
                    {"role": "user", "content": self._truncate(text, 12000)},
                ],
            )
            raw = response.choices[0].message.content or ""
            sections = self._parse_json_response(raw)
            if not isinstance(sections, list):
                return []

            chunks: list[SectionChunk] = []
            for sec in sections:
                if isinstance(sec, dict) and sec.get("section_id"):
                    chunks.append(
                        SectionChunk(
                            section_id=sec["section_id"],
                            title=sec.get("title", ""),
                            text=sec.get("text", ""),
                        )
                    )
            return chunks
        except Exception as exc:
            logger.warning("LLM 섹션 분할 실패: %s", exc)
            return []

    def _split_sections_heuristic(self, text: str) -> list[SectionChunk]:
        """휴리스틱으로 텍스트를 섹션별로 분할한다.

        대문자 제목이나 번호 매긴 헤더를 기준으로 분할한다.
        """
        # 제목 패턴: "1. xxx", "I. xxx", "## xxx", 전체 대문자 줄
        header_pattern = re.compile(
            r"^(?:"
            r"\d+\.\s+\S|"  # 1. Title
            r"[IVX]+\.\s+\S|"  # I. Title
            r"#{1,3}\s+\S|"  # ## Title
            r"[A-Z\s]{10,}$"  # ALL CAPS LINE
            r")",
            re.MULTILINE,
        )

        splits: list[tuple[int, str]] = []
        for match in header_pattern.finditer(text):
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.start())
            if line_end == -1:
                line_end = len(text)
            header = text[line_start:line_end].strip()
            splits.append((line_start, header))

        if not splits:
            section_id = self._guess_section_id(text)
            return [
                SectionChunk(
                    section_id=section_id,
                    title=section_id,
                    text=text,
                )
            ]

        chunks: list[SectionChunk] = []
        for i, (start, header) in enumerate(splits):
            end = splits[i + 1][0] if i + 1 < len(splits) else len(text)
            chunk_text = text[start:end].strip()
            section_id = self._guess_section_id(header + " " + chunk_text[:200])
            chunks.append(
                SectionChunk(
                    section_id=section_id,
                    title=header,
                    text=chunk_text,
                )
            )

        return chunks

    @staticmethod
    def _guess_section_id(text: str) -> str:
        """텍스트 내용으로 section_id를 추정한다."""
        text_lower = text.lower()
        best_match = "unknown"
        best_score = 0

        for section_id, patterns in _SECTION_PATTERNS.items():
            score = sum(1 for p in patterns if p in text_lower)
            if score > best_score:
                best_score = score
                best_match = section_id

        return best_match

    # -------------------------------------------------------------------
    # LLM 분석
    # -------------------------------------------------------------------

    async def _analyze_with_llm(self, text: str, section_id: str) -> str:
        """LLM을 사용하여 텍스트를 분석하고 템플릿 구조를 생성한다."""
        if not self._client:
            logger.warning("LLM 클라이언트 미설정, 휴리스틱 모드로 전환")
            return self._analyze_heuristic(text, section_id)

        user_prompt = _EXTRACTION_USER_TEMPLATE.format(
            section_id=section_id,
            text=self._truncate(text, 8000),
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                messages=[
                    {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("LLM 분석 실패: %s", exc)
            return self._analyze_heuristic(text, section_id)

    def _analyze_heuristic(self, text: str, section_id: str) -> str:
        """LLM 없이 휴리스틱으로 부동문자/슬롯을 분류한다.

        규칙:
        - 고유명사(기업명 등)가 반복되면 L2 후보
        - 수치 포함 문장은 L3 후보
        - 나머지는 L1 (부동문자)
        """
        lines = text.strip().split("\n")
        body_lines: list[str] = []
        slots: dict[str, dict[str, Any]] = {}
        slot_counter = 0

        # 수치 패턴
        number_pattern = re.compile(
            r"\d+(?:[,.]?\d+)*(?:\s*(?:억|백만|천|조|%|원|명|개|건))",
        )

        for line in lines:
            stripped = line.strip()
            if not stripped:
                body_lines.append("")
                continue

            # 수치가 많은 문장 → L3 슬롯 후보
            numbers = number_pattern.findall(stripped)
            if len(numbers) >= 2:
                slot_counter += 1
                slot_name = f"analysis_{slot_counter}"
                slots[slot_name] = {
                    "level": "L3",
                    "type": "sentence",
                    "hint": f"원문 참조: {stripped[:60]}...",
                    "max_tokens": max(60, len(stripped) // 2),
                    "data_keys": ["financial_statements", "derived_metrics"],
                }
                body_lines.append("{{" + slot_name + "}}")
            else:
                body_lines.append(stripped)

        result = {
            "section_id": section_id,
            "slots": slots,
            "body": "\n".join(body_lines),
            "conditional_blocks": [],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------------
    # 응답 파싱 / YAML 생성
    # -------------------------------------------------------------------

    @staticmethod
    def _parse_llm_response(raw: str) -> dict[str, Any] | None:
        """LLM 응답에서 JSON을 추출한다."""
        if not raw:
            return None

        # 전략 1: ```json ... ``` 블록
        code_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 전략 2: 전체 텍스트에서 { } 추출
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def _parse_json_response(raw: str) -> Any:
        """LLM 응답에서 JSON 배열 또는 객체를 추출한다."""
        if not raw:
            return None

        code_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # [ ] 또는 { } 추출
        for open_ch, close_ch in [("[", "]"), ("{", "}")]:
            start = raw.find(open_ch)
            end = raw.rfind(close_ch)
            if start != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    continue

        return None

    def _build_yaml(
        self,
        parsed: dict[str, Any],
        section_id: str,
        source_file: str,
    ) -> str:
        """파싱된 JSON을 YAML 템플릿 문자열로 변환한다."""
        section_id = parsed.get("section_id", section_id)

        # 헤더 주석
        lines: list[str] = [
            f"# {section_id} 템플릿 (자동 추출 초안)",
            "#",
            f"# 원본: {Path(source_file).name}",
            "# 주의: 자동 생성된 초안입니다. 반드시 수동 검토 후 사용하십시오.",
            "#",
            "# 마지막 수정: (자동 생성)",
            f"section_id: {section_id}",
            'version: "1.0"',
            f'source_reference: "{Path(source_file).name}"',
            "",
        ]

        # slots 섹션
        slots = parsed.get("slots", {})
        if slots:
            lines.append("slots:")
            # L2 먼저, L3 다음
            l2_slots = {
                k: v
                for k, v in slots.items()
                if isinstance(v, dict) and v.get("level") == "L2"
            }
            l3_slots = {
                k: v
                for k, v in slots.items()
                if isinstance(v, dict) and v.get("level") == "L3"
            }

            if l2_slots:
                lines.append("  # ── L2: 단순 치환 ──")
                for name, slot in l2_slots.items():
                    lines.extend(self._format_slot_yaml(name, slot))

            if l3_slots:
                lines.append("")
                lines.append("  # ── L3: LLM 생성 ──")
                for name, slot in l3_slots.items():
                    lines.extend(self._format_slot_yaml(name, slot))

        lines.append("")

        # body 섹션
        body = parsed.get("body", "")
        if body:
            lines.append("body: |")
            for body_line in body.split("\n"):
                lines.append(f"  {body_line}")
        lines.append("")

        # conditional_blocks 섹션
        cbs = parsed.get("conditional_blocks", [])
        if cbs:
            lines.append("conditional_blocks:")
            for cb in cbs:
                if isinstance(cb, dict):
                    condition = cb.get("condition", "")
                    insert_after = cb.get("insert_after", "")
                    text = cb.get("text", "")
                    lines.append(f'  - condition: "{condition}"')
                    lines.append(f"    insert_after: {insert_after}")
                    # 여러 줄이면 >- 사용
                    if "\n" in text:
                        lines.append("    text: >-")
                        for t_line in text.split("\n"):
                            lines.append(f"      {t_line.strip()}")
                    else:
                        lines.append(f'    text: "{self._escape_yaml_str(text)}"')
                    lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_slot_yaml(name: str, slot: dict[str, Any]) -> list[str]:
        """슬롯 정의를 YAML 줄로 변환한다."""
        lines: list[str] = [f"  {name}:"]
        level = slot.get("level", "L3")
        lines.append(f"    level: {level}")

        if level == "L2":
            source = slot.get("source", "")
            if source:
                lines.append(f"    source: {source}")
            default = slot.get("default", "")
            if default:
                lines.append(f'    default: "{default}"')
            fmt = slot.get("format", "")
            if fmt:
                lines.append(f"    format: {fmt}")
        elif level == "L3":
            slot_type = slot.get("type", "sentence")
            lines.append(f"    type: {slot_type}")
            hint = slot.get("hint", "")
            if hint:
                lines.append(f'    hint: "{hint}"')
            max_tokens = slot.get("max_tokens", 80)
            lines.append(f"    max_tokens: {max_tokens}")
            data_keys = slot.get("data_keys", [])
            if data_keys:
                lines.append("    data_keys:")
                for dk in data_keys:
                    lines.append(f"      - {dk}")

        lines.append("")
        return lines

    @staticmethod
    def _build_fallback_yaml(
        section_id: str,
        text: str,
        raw_response: str,
    ) -> str:
        """파싱 실패 시 원문을 주석으로 포함한 폴백 YAML을 생성한다."""
        lines: list[str] = [
            f"# {section_id} 템플릿 (자동 추출 실패 — 수동 편집 필요)",
            "#",
            "# LLM 응답 파싱 실패. 원문 텍스트를 body에 포함합니다.",
            "# 수동으로 {{slot}} 마커를 추가하고 slots 섹션을 작성하십시오.",
            "#",
            f"section_id: {section_id}",
            'version: "1.0"',
            "",
            "slots: {}",
            "",
            "body: |",
        ]
        for line in text.split("\n"):
            lines.append(f"  {line}")

        if raw_response:
            lines.append("")
            lines.append("# ── LLM 원본 응답 (참고용) ──")
            for line in raw_response.split("\n"):
                lines.append(f"# {line}")

        return "\n".join(lines)

    @staticmethod
    def _escape_yaml_str(s: str) -> str:
        """YAML 문자열에서 특수문자를 이스케이프한다."""
        return s.replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """텍스트를 최대 길이로 자른다."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n[... 이하 생략 ...]"
