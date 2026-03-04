"""IM PPTX 생성기 — Ralph Loop DocumentGenerator Protocol 구현.

IMPipeline + NarrativeOrchestrator를 래핑하여 Ralph Loop 오케스트레이터에서
사용할 수 있는 인터페이스를 제공한다.

핵심:
- generate_outline(): IMDocumentData의 active_sections → 아웃라인
- generate_section(): 단일 섹션의 내러티브 재생성 + PPTX 렌더링
- assemble_document(): 전체 PPTX 생성 (IMPipeline.generate)
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class IMDocumentGenerator:
    """IM PPTX 생성기 — Ralph Loop DocumentGenerator Protocol 구현.

    Args:
        im_data_dict: IMDocumentData를 직렬화한 dict.
        output_dir: PPTX 출력 디렉토리.
        feedback_enabled: 내러티브 재생성 시 피드백 주입 활성화.
    """

    def __init__(
        self,
        im_data_dict: dict[str, Any],
        output_dir: str = "",
        feedback_enabled: bool = True,
    ) -> None:
        self._im_data_dict = im_data_dict
        self._output_dir = output_dir or tempfile.mkdtemp(prefix="im_ralph_")
        self._feedback_enabled = feedback_enabled
        self._iteration_count = 0

    def _load_im_data(self) -> Any:
        """IMDocumentData를 복원한다."""
        from src.api.tasks.serializers import dict_to_im_data

        return dict_to_im_data(self._im_data_dict)

    async def generate_outline(
        self,
        source_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """IMDocumentData의 active_sections를 아웃라인으로 반환한다."""
        im_data = self._load_im_data()
        active_sections = im_data.get_active_sections()

        outline = []
        for section_id in active_sections:
            outline.append(
                {
                    "id": section_id,
                    "title": section_id.replace("_", " ").title(),
                    "memo_type": im_data.im_style.value if im_data.im_style else "IM",
                }
            )

        logger.info(
            "IM 아웃라인 생성: %d개 섹션 (%s)",
            len(outline),
            im_data.im_style.value if im_data.im_style else "IM",
        )
        return outline

    async def generate_section(
        self,
        section_id: str,
        section_criteria: dict[str, Any],
        source_data: dict[str, Any],
        feedback: list[str] | None = None,
    ) -> str:
        """단일 섹션의 내러티브를 재생성하고 전체 PPTX를 렌더링한다.

        IM PPTX는 섹션별 독립 PPTX가 아닌 전체 문서에서 섹션이 렌더링되므로,
        전체 PPTX를 생성한 후 경로를 반환한다.

        Args:
            section_id: 섹션 ID.
            section_criteria: PRD 섹션 기준.
            source_data: 원본 데이터.
            feedback: 이전 반복의 피드백 목록.

        Returns:
            생성된 PPTX 파일 경로.
        """
        self._iteration_count += 1
        im_data = self._load_im_data()

        # 1. 피드백이 있으면 내러티브 재생성
        if feedback and self._feedback_enabled:
            await self._regenerate_narrative_with_feedback(
                im_data,
                section_id,
                feedback,
            )

        # 2. 전체 PPTX 렌더링
        output_path = (
            Path(self._output_dir) / f"im_ralph_iter{self._iteration_count}.pptx"
        )
        pptx_path = await asyncio.to_thread(
            self._render_pptx,
            im_data,
            str(output_path),
        )

        logger.info(
            "IM PPTX 생성 (iteration=%d, section=%s): %s",
            self._iteration_count,
            section_id,
            pptx_path,
        )
        return pptx_path

    async def assemble_document(
        self,
        section_artifacts: dict[str, str],
        output_path: str,
    ) -> str:
        """최종 PPTX를 생성한다.

        가장 최근 iteration의 PPTX가 이미 전체 문서이므로,
        마지막 산출물을 최종 출력 경로로 복사한다.
        """
        import shutil

        # 가장 최근 산출물을 사용
        latest = None
        for artifact_path in section_artifacts.values():
            if artifact_path and Path(artifact_path).exists():
                latest = artifact_path

        if latest is None:
            logger.warning("조합할 섹션 산출물이 없습니다.")
            return ""

        if output_path:
            final_path = Path(output_path)
        else:
            final_path = Path(self._output_dir) / "im_ralph_final.pptx"

        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(latest, str(final_path))

        logger.info("IM Ralph Loop 최종 PPTX: %s", final_path)
        return str(final_path)

    async def _regenerate_narrative_with_feedback(
        self,
        im_data: Any,
        section_id: str,
        feedback: list[str],
    ) -> None:
        """피드백을 반영하여 내러티브를 재생성한다."""
        try:
            from src.narrative_generator.engine.orchestrator import (
                NarrativeOrchestrator,
            )

            orchestrator = NarrativeOrchestrator()
            result = orchestrator.generate(
                im_data,
                industry=im_data.industry or "",
                feedback_hints={section_id: feedback},
            )

            # 재생성된 내러티브를 im_data에 반영
            if result and result.narratives:
                im_data.narratives = result.narratives
                # 원본 dict도 업데이트
                from src.api.tasks.serializers import im_data_to_dict

                self._im_data_dict = im_data_to_dict(im_data)

            logger.info(
                "내러티브 재생성 완료 (feedback %d건, section=%s)",
                len(feedback),
                section_id,
            )
        except Exception as exc:
            logger.warning("내러티브 재생성 실패 (feedback 무시): %s", exc)

    def _render_pptx(self, im_data: Any, output_path: str) -> str:
        """동기적으로 PPTX를 렌더링한다."""
        from src.design_renderer.pipeline import IMPipeline

        pipeline = IMPipeline(continue_on_error=True)
        result = pipeline.generate(im_data, pptx_path=output_path)

        if not result.success:
            logger.warning(
                "PPTX 렌더링 경고: %d개 에러 — %s",
                len(result.errors),
                result.errors[:3],
            )

        return output_path
