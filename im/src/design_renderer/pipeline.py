"""E2E 파이프라인 — IMDocumentData → PPTX + PDF 듀얼 출력.

모든 섹션 렌더러를 오케스트레이션하여 PPTX와 PDF를
단일 코드베이스로 동시 생성한다.

Usage::

    pipeline = IMPipeline()
    result = pipeline.generate(
        data=im_data,
        pptx_path="output/im.pptx",
        pdf_path="output/im.pdf",
    )
    if result.success:
        print(f"Generated {result.total_pptx_slides} slides")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import IMDocumentData
from src.design_renderer.pdf_engine import (
    apply_pdf_security,
    build_watermark_css,
    generate_pdf,
)
from src.design_renderer.pdf_output.html_builder import build_html_document
from src.design_renderer.pptx_engine.slide_factory import SlideFactory
from src.design_renderer.manifest import GenerationManifest
from src.design_renderer.pptx_engine.font_helper import (
    ensure_ea_fonts_on_presentation,
)
from src.design_renderer.section_renderers.fallback import (
    render_fallback_slide_html,
    render_fallback_slide_pptx,
)
from src.design_renderer.pptx_engine.style_applier import (
    add_watermark,
    apply_presentation_style,
    set_edit_restriction,
)
from src.design_renderer.pptx_engine.template_manager import TemplateManager
from src.design_renderer.section_renderers import get_renderer
from src.design_renderer.security import SecurityOptions
from src.industry.exceptions import UnsupportedIndustryError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result 데이터클래스
# ---------------------------------------------------------------------------


@dataclass
class SectionResult:
    """개별 섹션 렌더링 결과."""

    section_id: str
    success: bool = True
    error: str | None = None
    pptx_slide_count: int = 0
    html_slide_count: int = 0


@dataclass
class PipelineResult:
    """E2E 파이프라인 실행 결과."""

    success: bool = True
    pptx_path: Path | None = None
    pdf_path: Path | None = None
    total_pptx_slides: int = 0
    total_pdf_pages: int = 0
    section_results: list[SectionResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    manifest: GenerationManifest | None = None

    @property
    def failed_sections(self) -> list[SectionResult]:
        """실패한 섹션 목록."""
        return [r for r in self.section_results if not r.success]

    @property
    def successful_sections(self) -> list[SectionResult]:
        """성공한 섹션 목록."""
        return [r for r in self.section_results if r.success]


# ---------------------------------------------------------------------------
# 파이프라인
# ---------------------------------------------------------------------------


class IMPipeline:
    """IM 문서 E2E 생성 파이프라인.

    IMDocumentData를 입력받아 PPTX/PDF 듀얼 출력을 생성한다.
    18종 섹션 렌더러를 순차 호출하며, 보안 옵션(워터마크, 암호화,
    편집 제한)을 후처리로 적용한다.

    Args:
        tokens: 디자인 토큰. None이면 DEFAULT_TOKENS.
        security: 보안 옵션. None이면 보안 미적용.
        template_path: PPTX 템플릿 경로. None이면 기본 템플릿.
        pdf_engine: PDF 엔진 ("auto" | "playwright" | "weasyprint").
        continue_on_error: True이면 개별 섹션 실패 시 계속 진행.
    """

    def __init__(
        self,
        *,
        tokens: IMDesignTokens | None = None,
        security: SecurityOptions | None = None,
        template_path: Path | None = None,
        pdf_engine: str = "auto",
        continue_on_error: bool = True,
    ) -> None:
        self._tokens = tokens or DEFAULT_TOKENS
        self._security = security
        self._template_path = template_path
        self._pdf_engine = pdf_engine
        self._continue_on_error = continue_on_error

    def generate(
        self,
        data: IMDocumentData,
        *,
        pptx_path: str | Path | None = None,
        pdf_path: str | Path | None = None,
    ) -> PipelineResult:
        """PPTX + PDF 듀얼 출력 생성.

        Args:
            data: IM 문서 입력 데이터.
            pptx_path: PPTX 저장 경로. None이면 PPTX 미생성.
            pdf_path: PDF 저장 경로. None이면 PDF 미생성.

        Returns:
            파이프라인 실행 결과.
        """
        start = time.monotonic()
        result = PipelineResult()

        # 1. 파생 지표 계산
        data.compute_derived_metrics()

        # 1.5. 산업 모듈 resolve (Phase A1)
        industry_context = None
        if data.industry:
            try:
                from src.industry.registry import get_industry_module_safe

                industry_module = get_industry_module_safe(data.industry)
                industry_context = industry_module.get_context()
                logger.info(
                    "산업 모듈 로드: %s (%s)",
                    industry_context.industry_name_kr,
                    data.industry,
                )
            except UnsupportedIndustryError as e:
                result.warnings.append(f"산업 모듈 로드 실패: {e.message}")
                logger.warning("산업 모듈 로드 실패: %s", e.message)

        # 2. 활성 섹션 결정
        active_sections = data.get_active_sections()
        logger.info(
            f"파이프라인 시작: {data.project_name}, "
            f"{len(active_sections)}개 섹션 ({data.im_style.value})"
        )

        # 3. PPTX 인프라 초기화
        manager = TemplateManager(tokens=self._tokens)
        prs = manager.new_presentation()
        factory = SlideFactory(manager, prs=prs, tokens=self._tokens)

        # 4. 섹션별 듀얼 렌더링 (매니페스트 + 폴백 슬라이드)
        all_html_slides: list[str] = []
        manifest = GenerationManifest()

        for section_id in active_sections:
            sec_result = SectionResult(section_id=section_id)
            sec_start = time.monotonic()
            try:
                renderer = get_renderer(section_id)

                # PPTX 렌더링
                pptx_slides = renderer.render_pptx(
                    factory, data, prs=prs, tokens=self._tokens
                )
                sec_result.pptx_slide_count = len(pptx_slides)

                # HTML 렌더링 (PDF용)
                html_slides = renderer.render_html(data, tokens=self._tokens)
                sec_result.html_slide_count = len(html_slides)
                all_html_slides.extend(html_slides)

                render_ms = (time.monotonic() - sec_start) * 1000
                manifest.add_entry(
                    section_id,
                    title=section_id.replace("_", " ").title(),
                    success=True,
                    render_time_ms=render_ms,
                    slide_count=sec_result.pptx_slide_count,
                )

            except Exception as e:
                render_ms = (time.monotonic() - sec_start) * 1000
                sec_result.success = False
                sec_result.error = str(e)
                result.errors.append(f"[{section_id}] {e}")
                logger.error(f"섹션 '{section_id}' 렌더링 실패: {e}")

                manifest.add_entry(
                    section_id,
                    title=section_id.replace("_", " ").title(),
                    success=False,
                    error=str(e),
                    render_time_ms=render_ms,
                )

                if self._continue_on_error:
                    # 폴백 슬라이드 삽입
                    try:
                        render_fallback_slide_pptx(
                            factory, section_id, str(e),
                            prs=prs, tokens=self._tokens,
                        )
                        fallback_html = render_fallback_slide_html(
                            section_id, str(e), tokens=self._tokens,
                        )
                        all_html_slides.append(fallback_html)
                        sec_result.pptx_slide_count = 1
                        sec_result.html_slide_count = 1
                    except Exception as fallback_err:
                        logger.error(
                            f"폴백 슬라이드 생성도 실패: {fallback_err}"
                        )
                else:
                    result.success = False
                    result.elapsed_seconds = time.monotonic() - start
                    result.section_results.append(sec_result)
                    manifest.total_elapsed_ms = (
                        time.monotonic() - start
                    ) * 1000
                    result.manifest = manifest
                    return result

            result.section_results.append(sec_result)

        manifest.total_elapsed_ms = (time.monotonic() - start) * 1000
        result.manifest = manifest

        # 5. PPTX 후처리: 스타일 + 한글 폰트 + 보안
        apply_presentation_style(prs, tokens=self._tokens)

        # 5-1. 한글 폰트 a:ea 후처리 — 모든 text run에 동아시아 폰트 보장
        ea_font = self._tokens.typography.font_body
        ea_count = ensure_ea_fonts_on_presentation(prs, ea_font=ea_font)
        if ea_count > 0:
            result.warnings.append(
                f"a:ea 폰트 후처리: {ea_count}개 run에 '{ea_font}' 추가"
            )

        if self._security:
            self._apply_pptx_security(prs)

        # 6. PPTX 저장
        if pptx_path:
            out = Path(pptx_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            prs.save(str(out))
            result.pptx_path = out
            logger.info(f"PPTX 저장 완료: {out}")

        result.total_pptx_slides = len(prs.slides)

        # 7. HTML 조립 + PDF 생성
        if pdf_path and all_html_slides:
            html_doc = build_html_document(
                all_html_slides,
                title=data.project_name or "Information Memorandum",
                tokens=self._tokens,
            )

            # 워터마크 CSS 주입
            if self._security and self._security.watermark_text:
                wm_css = build_watermark_css(
                    self._security.watermark_text,
                    opacity=self._security.watermark_opacity,
                    color=self._security.watermark_color,
                    font_size=self._security.watermark_font_size,
                    position=self._security.watermark_position.value,
                )
                html_doc = html_doc.replace("</style>", f"\n{wm_css}\n</style>")

            generate_pdf(
                html_doc,
                output_path=pdf_path,
                tokens=self._tokens,
                engine=self._pdf_engine,
            )

            # PDF 암호화 적용
            if self._security and self._security.pdf_password:
                apply_pdf_security(
                    pdf_path,
                    user_password=self._security.pdf_password,
                    owner_password=self._security.pdf_owner_password or "",
                    restrict_print=self._security.pdf_restrict_print,
                    restrict_copy=self._security.pdf_restrict_copy,
                    restrict_modify=self._security.pdf_restrict_modify,
                )

            result.pdf_path = Path(pdf_path)
            logger.info(f"PDF 저장 완료: {pdf_path}")

        result.total_pdf_pages = len(all_html_slides)

        # 8. 결과 집계
        if result.failed_sections:
            result.warnings.append(
                f"{len(result.failed_sections)}개 섹션 렌더링 실패: "
                f"{[r.section_id for r in result.failed_sections]}"
            )

        result.success = len(result.errors) == 0
        result.elapsed_seconds = time.monotonic() - start

        logger.info(
            f"파이프라인 완료: {result.total_pptx_slides} PPTX 슬라이드, "
            f"{result.total_pdf_pages} PDF 페이지, "
            f"{result.elapsed_seconds:.1f}초"
        )
        return result

    def generate_pptx(
        self,
        data: IMDocumentData,
        *,
        output_path: str | Path,
    ) -> PipelineResult:
        """PPTX만 생성 (PDF 미생성).

        Args:
            data: IM 문서 입력 데이터.
            output_path: PPTX 저장 경로.

        Returns:
            파이프라인 실행 결과.
        """
        return self.generate(data, pptx_path=output_path, pdf_path=None)

    def generate_pdf(
        self,
        data: IMDocumentData,
        *,
        output_path: str | Path,
    ) -> PipelineResult:
        """PDF만 생성 (PPTX 미생성).

        Args:
            data: IM 문서 입력 데이터.
            output_path: PDF 저장 경로.

        Returns:
            파이프라인 실행 결과.
        """
        return self.generate(data, pptx_path=None, pdf_path=output_path)

    def _apply_pptx_security(self, prs: Any) -> None:
        """PPTX 보안 옵션 일괄 적용."""
        security = self._security
        if security is None:
            return

        if security.watermark_text:
            add_watermark(
                prs,
                text=security.watermark_text,
                opacity=security.watermark_opacity,
                color_hex=security.watermark_color,
                font_size=security.watermark_font_size,
                skip_first_slide=True,
                tokens=self._tokens,
            )

        if security.pptx_read_only or security.pptx_edit_password:
            set_edit_restriction(
                prs,
                read_only=security.pptx_read_only,
                password=security.pptx_edit_password,
            )
