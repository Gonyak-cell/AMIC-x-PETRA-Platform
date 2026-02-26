"""Excel Financial Model Ralph Loop 통합 생성기.

FinancialModelBuilder를 래핑하여 DocumentGenerator Protocol을 구현한다.
각 워크시트를 1 섹션으로 매핑하여 Ralph Loop 오케스트레이터와 호환한다.
"""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from app.excel.model_builder import SHEET_CONFIG, FinancialModelBuilder
from app.models.enums import FinancialModelType

logger = logging.getLogger(__name__)

# 시트 이름 → PRD 섹션 제목 매핑
SHEET_TITLES: dict[str, str] = {
    "Legend": "Legend / Color Key",
    "Input": "Input / Assumptions",
    "IS": "Income Statement",
    "BS": "Balance Sheet",
    "CF": "Cash Flow Statement",
    "WACC": "WACC Calculation",
    "DCF": "DCF Valuation",
    "GPCM": "Guideline Public Company Method",
    "GTM": "Guideline Transaction Method",
    "Sensitivity": "Sensitivity Analysis",
    "Football Field": "Football Field",
    "Summary": "Valuation Summary",
    "Sources & Uses": "Sources & Uses",
    "Debt Schedule": "Debt Schedule",
    "Returns": "Returns Analysis",
    "Revenue Build-Up": "Revenue Build-Up",
    "Cost Structure": "Cost Structure",
}


class RalphExcelGenerator:
    """Ralph Loop 오케스트레이터와 호환되는 Excel 재무모델 생성기.

    DocumentGenerator Protocol:
    - generate_outline() → 워크시트 구조 (섹션 목록)
    - generate_section() → 섹션별 임시 Excel 파일 생성
    - assemble_document() → 최종 .xlsx 생성
    """

    def __init__(
        self,
        model_type: FinancialModelType,
        title: str,
        checklist_values: dict[str, str] | None = None,
        parameters: dict[str, Any] | None = None,
        llm_call: Any = None,
    ) -> None:
        self.model_type = model_type
        self.title = title
        self.checklist_values = checklist_values or {}
        self.parameters = parameters or {}
        self._llm_call = llm_call
        self._temp_dir = Path(tempfile.mkdtemp(prefix="ralph_excel_"))

    def cleanup(self) -> None:
        """임시 디렉토리를 삭제한다. 오케스트레이터 완료 후 호출."""
        if self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            logger.debug("임시 디렉토리 정리: %s", self._temp_dir)

    def __del__(self) -> None:
        try:
            self.cleanup()
        except Exception:
            pass

    async def generate_outline(
        self,
        source_data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """모델 유형에 따른 워크시트 목록을 반환한다."""
        sheets = SHEET_CONFIG.get(self.model_type, SHEET_CONFIG[FinancialModelType.DCF])
        return [
            {
                "id": sheet_name,
                "title": SHEET_TITLES.get(sheet_name, sheet_name),
            }
            for sheet_name in sheets
        ]

    async def generate_section(
        self,
        section_id: str,
        section_criteria: dict[str, Any] | None = None,
        source_data: dict[str, Any] | None = None,
        feedback: list[str] | None = None,
    ) -> str:
        """워크시트 하나를 빌드하고 임시 .xlsx 파일 경로를 반환한다.

        LLM이 있을 때: 피드백을 반영하여 checklist_values를 LLM이 보완한 후 빌드.
        LLM이 없을 때: FinancialModelBuilder의 해당 시트 빌더를 직접 호출.
        """
        # 피드백이 있고 LLM이 연결된 경우: 체크리스트 값 보완
        effective_values = dict(self.checklist_values)
        if feedback and self._llm_call:
            try:
                effective_values = await self._refine_values_with_llm(
                    section_id,
                    effective_values,
                    feedback,
                    section_criteria,
                )
                # 개선된 값을 축적하여 assemble_document()에서 사용
                self.checklist_values.update(effective_values)
            except Exception as e:
                logger.warning("LLM 값 보완 실패, 원본 사용: %s", e)

        # FinancialModelBuilder로 전체 워크북을 빌드하되, 해당 시트만 포함하는 임시 파일 생성
        builder = FinancialModelBuilder(
            model_type=self.model_type,
            title=self.title,
            checklist_values=effective_values,
            parameters=self.parameters,
        )
        builder.build()

        # 해당 시트가 있는지 확인
        if section_id not in builder.wb.sheetnames:
            logger.warning("시트 '%s' 없음 — 전체 워크북 임시 파일 반환", section_id)

        # 임시 파일 저장
        temp_path = self._temp_dir / f"{section_id}_{uuid.uuid4().hex[:8]}.xlsx"
        builder.wb.save(str(temp_path))
        return str(temp_path)

    async def assemble_document(
        self,
        section_artifacts: dict[str, str],
        output_path: str | None = None,
    ) -> str:
        """전체 워크북을 최종 .xlsx로 생성한다.

        NOTE: section_artifacts(개별 시트 임시 파일)는 Gate 평가용으로만 사용되며,
        최종 워크북은 self.checklist_values를 기준으로 전체를 재빌드한다.
        LLM이 연결된 경우 generate_section()에서 _refine_values_with_llm()이
        self.checklist_values를 in-place 업데이트하므로 개선된 값이 반영된다.
        LLM 미연결 시에는 초기 checklist_values가 그대로 사용된다 (의도적 설계).
        """
        if not output_path:
            output_dir = self._temp_dir / "final"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / f"{self.model_type.value}_{uuid.uuid4().hex[:8]}.xlsx")

        # 최종 빌드 — self.checklist_values 기준 전체 워크북 재생성
        builder = FinancialModelBuilder(
            model_type=self.model_type,
            title=self.title,
            checklist_values=self.checklist_values,
            parameters=self.parameters,
        )
        saved = builder.save(output_path)
        logger.info(
            "Excel 최종 생성: %s (%d sheets)",
            saved.name,
            len(builder.wb.sheetnames),
        )
        return str(saved)

    async def _refine_values_with_llm(
        self,
        section_id: str,
        values: dict[str, str],
        feedback: list[str],
        criteria: dict[str, Any] | None,
    ) -> dict[str, str]:
        """LLM을 사용하여 피드백 기반으로 체크리스트 값을 보완한다."""
        system_prompt = (
            "당신은 IB(Investment Bank)급 재무모델 전문가입니다.\n"
            f"워크시트: {section_id}\n"
            "이전 평가 피드백을 반영하여 가정값을 개선하세요.\n"
            '반드시 JSON 형식으로 {"key": "value"} 형태로만 응답하세요.'
        )

        user_prompt = (
            f"## 현재 가정값\n{json.dumps(values, ensure_ascii=False)[:3000]}\n\n"
            f"## 이전 피드백\n" + "\n".join(f"- {f}" for f in feedback) + "\n\n"
        )
        if criteria:
            user_prompt += f"## 수용 기준\n{json.dumps(criteria, ensure_ascii=False)[:2000]}\n\n"
        user_prompt += "## 개선된 가정값 (JSON)\n"

        raw = await self._llm_call(system_prompt, user_prompt)
        text = raw if isinstance(raw, str) else str(raw)

        # JSON 추출
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0]

        try:
            refined = json.loads(text.strip())
            if isinstance(refined, dict):
                merged = dict(values)
                merged.update({k: str(v) for k, v in refined.items()})
                return merged
        except json.JSONDecodeError:
            logger.warning("LLM 응답 JSON 파싱 실패")

        return values
