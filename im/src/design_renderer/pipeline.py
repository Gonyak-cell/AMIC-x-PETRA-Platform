"""E2E 파이프라인 — IMDocumentData → PPTX 출력.

모든 섹션 렌더러를 오케스트레이션하여 PPTX를 생성한다.
PDF 출력은 제거됨 (PPTX 전용).

Usage::

    pipeline = IMPipeline()
    result = pipeline.generate_pptx(
        data=im_data,
        output_path="output/im.pptx",
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
from src.design_renderer.pptx_engine.slide_factory import SlideFactory
from src.design_renderer.manifest import GenerationManifest
from src.design_renderer.pptx_engine.font_helper import (
    ensure_ea_fonts_on_presentation,
)
from src.design_renderer.section_renderers.fallback import (
    render_fallback_slide_pptx,
)
from src.design_renderer.pptx_engine.style_applier import (
    add_watermark,
    apply_presentation_style,
    set_edit_restriction,
)
from src.design_renderer.pptx_engine.template_manager import TemplateManager
from src.design_renderer.section_renderers import RendererNotFoundError, get_renderer
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
    template_load_ms: int = 0
    persist_ms: int = 0
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
    """IM 문서 E2E 생성 파이프라인 (PPTX 전용).

    IMDocumentData를 입력받아 PPTX를 생성한다.
    32종 섹션 렌더러(IM 18종 + TM 8종 + DM 6종)를 순차 호출하며, 보안 옵션(워터마크,
    편집 제한)을 후처리로 적용한다.

    Args:
        tokens: 디자인 토큰. None이면 DEFAULT_TOKENS.
        security: 보안 옵션. None이면 보안 미적용.
        template_path: PPTX 템플릿 경로. None이면 기본 템플릿.
        continue_on_error: True이면 개별 섹션 실패 시 계속 진행.
    """

    def __init__(
        self,
        *,
        tokens: IMDesignTokens | None = None,
        security: SecurityOptions | None = None,
        template_path: Path | None = None,
        continue_on_error: bool = True,
    ) -> None:
        self._tokens = tokens or DEFAULT_TOKENS
        self._security = security
        self._template_path = template_path
        self._continue_on_error = continue_on_error

    def generate(
        self,
        data: IMDocumentData,
        *,
        pptx_path: str | Path | None = None,
        pdf_path: str | Path | None = None,
    ) -> PipelineResult:
        """PPTX (및 향후 PDF) 생성.

        Args:
            data: IM 문서 입력 데이터.
            pptx_path: PPTX 저장 경로. None이면 저장 없이 결과만 반환.
            pdf_path: PDF 저장 경로. 현재 미지원 (향후 구현 예정).

        Returns:
            파이프라인 실행 결과.
        """
        start = time.monotonic()
        result = PipelineResult()

        # 1. 파생 지표 계산
        data.compute_derived_metrics()

        # 1.5. 산업 모듈 resolve (Phase A1)
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
        _tpl_t0 = time.monotonic()
        prs = manager.new_presentation()
        result.template_load_ms = int((time.monotonic() - _tpl_t0) * 1000)
        factory = SlideFactory(manager, prs=prs, tokens=self._tokens)

        # 4. 섹션별 PPTX 렌더링 (매니페스트 + 폴백 슬라이드)
        manifest = GenerationManifest()

        # TM (Teaser) 모드: 2-pass 렌더링으로 TOC 페이지 번호 자동 계산
        from src.design_renderer.im_document import IMStyle

        if data.im_style == IMStyle.TEASER:
            self._render_tm_sections(
                data,
                factory,
                prs,
                manifest,
                result,
                start,
            )
            # TM 모드에서는 for 루프 건너뜀
            active_sections = []

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

                render_ms = (time.monotonic() - sec_start) * 1000
                manifest.add_entry(
                    section_id,
                    title=section_id.replace("_", " ").title(),
                    success=True,
                    render_time_ms=render_ms,
                    slide_count=sec_result.pptx_slide_count,
                )

            except RendererNotFoundError as e:
                render_ms = (time.monotonic() - sec_start) * 1000
                sec_result.success = False
                sec_result.error = str(e)
                result.errors.append(f"[{section_id}] 미등록 렌더러: {e}")
                logger.warning("미등록 섹션 렌더러 '%s': %s", section_id, e)
            except Exception as e:
                render_ms = (time.monotonic() - sec_start) * 1000
                sec_result.success = False
                sec_result.error = str(e)
                result.errors.append(f"[{section_id}] {e}")
                logger.error("섹션 '%s' 렌더링 실패: %s", section_id, e, exc_info=True)

                manifest.add_entry(
                    section_id,
                    title=section_id.replace("_", " ").title(),
                    success=False,
                    error=str(e),
                    render_time_ms=render_ms,
                )

                if self._continue_on_error:
                    try:
                        render_fallback_slide_pptx(
                            factory,
                            section_id,
                            str(e),
                            prs=prs,
                            tokens=self._tokens,
                        )
                        sec_result.pptx_slide_count = 1
                        # 폴백 성공: errors → warnings 이동 (success 판정에 영향 안 줌)
                        fallback_msg = result.errors.pop()
                        result.warnings.append(f"{fallback_msg} (폴백 적용)")
                    except Exception as fallback_err:
                        logger.error(f"폴백 슬라이드 생성도 실패: {fallback_err}")
                else:
                    result.success = False
                    result.elapsed_seconds = time.monotonic() - start
                    result.section_results.append(sec_result)
                    manifest.total_elapsed_ms = (time.monotonic() - start) * 1000
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
            logger.info(f"a:ea 폰트 후처리: {ea_count}개 run에 '{ea_font}' 추가")

        if self._security:
            self._apply_pptx_security(prs)

        # 6. PPTX 저장
        if pptx_path:
            out = Path(pptx_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            _persist_t0 = time.monotonic()
            prs.save(str(out))
            result.persist_ms = int((time.monotonic() - _persist_t0) * 1000)
            result.pptx_path = out
            logger.info(f"PPTX 저장 완료: {out}")

        result.total_pptx_slides = len(prs.slides)

        # 6-1. PDF 변환 (향후 구현 예정)
        # TODO: pdf_path가 주어지면 PPTX → PDF 변환 수행
        if pdf_path:
            logger.info("PDF 변환은 아직 미지원: pdf_path=%s (무시)", pdf_path)

        # 7. 결과 집계
        if result.failed_sections:
            result.warnings.append(
                f"{len(result.failed_sections)}개 섹션 렌더링 실패 (폴백 적용): "
                f"{[r.section_id for r in result.failed_sections]}"
            )

        # continue_on_error 모드에서 폴백이 적용된 섹션 실패는 warnings로만 처리.
        # errors 리스트에 치명적 오류(PPTX 생성 불가 등)만 남긴다.
        result.success = len(result.errors) == 0
        result.elapsed_seconds = time.monotonic() - start

        logger.info(
            f"파이프라인 완료: {result.total_pptx_slides} PPTX 슬라이드, "
            f"{result.elapsed_seconds:.1f}초"
        )
        return result

    def generate_pptx(
        self,
        data: IMDocumentData,
        *,
        output_path: str | Path,
    ) -> PipelineResult:
        """PPTX 생성 (편의 메서드).

        Gate A(Template Preflight)를 실행한 후 generate()를 호출한다.
        preflight 실패 시 즉시 PipelineResult(success=False)를 반환한다.

        Args:
            data: IM 문서 입력 데이터.
            output_path: PPTX 저장 경로.

        Returns:
            파이프라인 실행 결과.
        """
        # Gate A: Template Preflight — 렌더링 전 템플릿 무결성 검증
        if self._template_path:
            try:
                from src.template_engine.template_spec import get_spec

                spec = get_spec(data.im_style.value.upper())
                if spec:
                    import asyncio

                    from src.quality_gate.template_preflight import (
                        TemplatePreflight,
                    )

                    preflight = TemplatePreflight()

                    # 동기 컨텍스트에서 async evaluate 호출
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None

                    if loop and loop.is_running():
                        # 이미 이벤트 루프 실행 중 — 새 스레드에서 실행
                        import concurrent.futures

                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            preflight_result = pool.submit(
                                lambda: asyncio.run(
                                    preflight.evaluate(
                                        str(self._template_path),
                                        prd_section={
                                            "im_style": data.im_style.value,
                                        },
                                        source_data={"template_spec": spec},
                                    )
                                )
                            ).result()
                    else:
                        preflight_result = asyncio.run(
                            preflight.evaluate(
                                str(self._template_path),
                                prd_section={
                                    "im_style": data.im_style.value,
                                },
                                source_data={"template_spec": spec},
                            )
                        )

                    if not preflight_result.passed:
                        logger.error(
                            "Gate A 프리플라이트 실패: %s",
                            preflight_result.issues,
                        )
                        return PipelineResult(
                            success=False,
                            errors=[
                                f"템플릿 프리플라이트 실패: {preflight_result.issues}",
                            ],
                        )
            except Exception as preflight_exc:
                logger.warning(
                    "Gate A 프리플라이트 실행 중 예외 (계속 진행): %s",
                    preflight_exc,
                )

        return self.generate(data, pptx_path=output_path)

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

    # ------------------------------------------------------------------
    # TM (Teaser Memorandum) 2-pass 렌더링
    # ------------------------------------------------------------------

    def _render_tm_sections(
        self,
        data: IMDocumentData,
        factory: SlideFactory,
        prs: Any,
        manifest: GenerationManifest,
        result: PipelineResult,
        start: float,
    ) -> None:
        """TM 전용 2-pass PPTX 렌더링.

        Phase 1: cover + disclaimer 렌더링
        Phase 2: 각 그룹별 TOC 빈 슬라이드 + 콘텐츠 섹션 렌더링
        Phase 3: contact 렌더링
        Phase 4: TOC 슬라이드에 올바른 페이지 번호 주입
        """
        from src.design_renderer.im_document import TEASER_TOC_GROUPS
        from src.design_renderer.pptx_engine.toc_builder import (
            build_tm_toc_slide,
        )

        # --- Phase 1: cover + disclaimer ---
        for section_id in ("cover", "disclaimer"):
            self._render_single_section(
                section_id,
                data,
                factory,
                prs,
                manifest,
                result,
                start,
            )

        # --- Phase 2: 그룹별 TOC placeholder + 콘텐츠 ---
        current_slide_idx = len(prs.slides)  # cover + disclaimer 후 인덱스
        toc_placeholder_slides: list[tuple[str, Any]] = []  # (key, slide)
        group_start_pages: dict[str, int] = {}

        for group in TEASER_TOC_GROUPS:
            group_key = group["key"]
            subsections = [s[0] for s in group["subsections"]]

            # TOC placeholder 슬라이드 (FOREST 배경)
            toc_slide = factory.add_forest_slide(prs)
            toc_placeholder_slides.append((group_key, toc_slide))
            current_slide_idx += 1

            # 이 그룹의 콘텐츠 시작 페이지 (1-based)
            group_start_pages[group_key] = current_slide_idx + 1

            for section_id in subsections:
                pptx_count = self._render_single_section(
                    section_id,
                    data,
                    factory,
                    prs,
                    manifest,
                    result,
                    start,
                )
                current_slide_idx += pptx_count

        # --- Phase 3: contact ---
        self._render_single_section(
            "contact",
            data,
            factory,
            prs,
            manifest,
            result,
            start,
        )

        # --- Phase 4: PPTX TOC 슬라이드 채우기 ---
        for group_key, toc_slide in toc_placeholder_slides:
            build_tm_toc_slide(
                toc_slide,
                current_group=group_key,
                page_numbers=group_start_pages,
                tokens=self._tokens,
            )

        # --- Phase 5: TOC 페이지 번호 유효성 검증 ---
        total_slides = len(prs.slides)
        for group_key, page_num in group_start_pages.items():
            if page_num > total_slides:
                logger.warning(
                    "TOC 페이지 번호 불일치: 그룹 '%s' → %d페이지, "
                    "전체 슬라이드 수: %d",
                    group_key,
                    page_num,
                    total_slides,
                )

        logger.info(
            "TM 2-pass 렌더링 완료: 4그룹 TOC, 페이지 번호: %s, 총 슬라이드: %d",
            group_start_pages,
            total_slides,
        )

    def _render_single_section(
        self,
        section_id: str,
        data: IMDocumentData,
        factory: SlideFactory,
        prs: Any,
        manifest: GenerationManifest,
        result: PipelineResult,
        start: float,
    ) -> int:
        """단일 섹션 PPTX 렌더링 (TM 내부용).

        Returns:
            생성된 PPTX 슬라이드 수.
        """
        sec_result = SectionResult(section_id=section_id)
        sec_start = time.monotonic()
        try:
            renderer = get_renderer(section_id)
            pptx_slides = renderer.render_pptx(
                factory, data, prs=prs, tokens=self._tokens
            )
            sec_result.pptx_slide_count = len(pptx_slides)

            render_ms = (time.monotonic() - sec_start) * 1000
            manifest.add_entry(
                section_id,
                title=section_id.replace("_", " ").title(),
                success=True,
                render_time_ms=render_ms,
                slide_count=sec_result.pptx_slide_count,
            )
            result.section_results.append(sec_result)
            return len(pptx_slides)

        except Exception as e:
            render_ms = (time.monotonic() - sec_start) * 1000
            sec_result.success = False
            sec_result.error = str(e)
            result.errors.append(f"[{section_id}] {e}")
            logger.error(f"TM 섹션 '{section_id}' 렌더링 실패: {e}")

            manifest.add_entry(
                section_id,
                title=section_id.replace("_", " ").title(),
                success=False,
                error=str(e),
                render_time_ms=render_ms,
            )

            if self._continue_on_error:
                try:
                    render_fallback_slide_pptx(
                        factory,
                        section_id,
                        str(e),
                        prs=prs,
                        tokens=self._tokens,
                    )
                    sec_result.pptx_slide_count = 1
                    result.section_results.append(sec_result)
                    return 1
                except Exception as fallback_err:
                    logger.error(f"TM 폴백 슬라이드 생성도 실패: {fallback_err}")

            result.section_results.append(sec_result)
            return 0
