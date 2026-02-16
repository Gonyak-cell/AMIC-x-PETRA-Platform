"""HTML→PDF 변환 엔진 — Playwright 우선 + WeasyPrint 폴백.

Radar amic_report.py 패턴을 IM 레이아웃(10.83"×7.5")에 맞게 적용.
폰트 WOFF2 base64 임베딩으로 브라우저/WeasyPrint 모두 동작한다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Playwright 엔진
# ---------------------------------------------------------------------------


def _generate_pdf_with_playwright(
    html_content: str,
    tokens: IMDesignTokens,
) -> bytes:
    """Playwright/Chromium으로 PDF 생성.

    Args:
        html_content: 완전한 HTML 문서 문자열.
        tokens: 디자인 토큰 (페이지 크기 참조).

    Returns:
        PDF 바이트 데이터.
    """
    from playwright.sync_api import sync_playwright

    lay = tokens.layout
    # inches → mm (1 inch = 25.4mm)
    width_mm = lay.page_width * 25.4
    height_mm = lay.page_height * 25.4

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")

        pdf_bytes: bytes = page.pdf(
            width=f"{width_mm}mm",
            height=f"{height_mm}mm",
            print_background=True,
            margin={
                "top": "0mm",
                "bottom": "0mm",
                "left": "0mm",
                "right": "0mm",
            },
        )

        browser.close()

    return pdf_bytes


# ---------------------------------------------------------------------------
# WeasyPrint 엔진
# ---------------------------------------------------------------------------


def _generate_pdf_with_weasyprint(
    html_content: str,
    tokens: IMDesignTokens,
) -> bytes:
    """WeasyPrint으로 PDF 생성 (Playwright 폴백용).

    Args:
        html_content: 완전한 HTML 문서 문자열.
        tokens: 디자인 토큰 (페이지 크기 참조).

    Returns:
        PDF 바이트 데이터.
    """
    from weasyprint import CSS, HTML

    lay = tokens.layout
    page_css = CSS(
        string=f"""
        @page {{
            size: {lay.page_width}in {lay.page_height}in;
            margin: 0;
        }}
        """
    )

    html_doc = HTML(string=html_content)
    pdf_bytes: bytes = html_doc.write_pdf(stylesheets=[page_css])

    return pdf_bytes


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------


def generate_pdf(
    html_content: str,
    *,
    output_path: str | Path | None = None,
    tokens: IMDesignTokens | None = None,
    engine: str = "auto",
) -> bytes:
    """HTML을 PDF로 변환.

    Playwright/Chromium 사용을 시도하고, 브라우저가 설치되지 않은 경우
    WeasyPrint으로 폴백한다.

    Args:
        html_content: 완전한 HTML 문서 문자열 (CSS/폰트 포함).
        output_path: PDF 저장 경로 (선택). None이면 파일 저장 안 함.
        tokens: 디자인 토큰.
        engine: "auto" (기본: Playwright→WeasyPrint) | "playwright" | "weasyprint"

    Returns:
        PDF 바이트 데이터.

    Raises:
        RuntimeError: 모든 엔진이 실패한 경우.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    pdf_bytes: bytes
    engine_used: str

    if engine == "weasyprint":
        pdf_bytes = _generate_pdf_with_weasyprint(html_content, tokens)
        engine_used = "WeasyPrint"
    elif engine == "playwright":
        pdf_bytes = _generate_pdf_with_playwright(html_content, tokens)
        engine_used = "Playwright"
    else:
        # auto: Playwright 우선, WeasyPrint 폴백
        try:
            pdf_bytes = _generate_pdf_with_playwright(html_content, tokens)
            engine_used = "Playwright"
        except ImportError:
            logger.warning("Playwright 미설치, WeasyPrint으로 폴백")
            pdf_bytes = _generate_pdf_with_weasyprint(html_content, tokens)
            engine_used = "WeasyPrint"
        except Exception as e:
            error_msg = str(e)
            if (
                "Executable doesn't exist" in error_msg
                or "browser" in error_msg.lower()
            ):
                logger.warning(
                    f"Playwright 브라우저 미설치, WeasyPrint으로 폴백: {e}"
                )
                pdf_bytes = _generate_pdf_with_weasyprint(html_content, tokens)
                engine_used = "WeasyPrint"
            else:
                raise

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf_bytes)
        logger.info(f"IM PDF 저장 ({engine_used}): {out}")

    logger.info(
        f"PDF 생성 완료 ({engine_used}): {len(pdf_bytes):,} bytes"
    )
    return pdf_bytes


# ---------------------------------------------------------------------------
# PDF 보안 (암호화 + 권한 제한)
# ---------------------------------------------------------------------------


def apply_pdf_security(
    pdf_path: str | Path,
    *,
    user_password: str = "",
    owner_password: str = "",
    restrict_print: bool = True,
    restrict_copy: bool = True,
    restrict_modify: bool = True,
    output_path: str | Path | None = None,
) -> Path:
    """기존 PDF에 비밀번호 보호 및 권한 제한 적용.

    pikepdf(AES-256) 우선, PyPDF2 폴백.

    Args:
        pdf_path: 입력 PDF 파일 경로.
        user_password: 열기 비밀번호.
        owner_password: 소유자 비밀번호 (권한 제어).
        restrict_print: True이면 인쇄 제한.
        restrict_copy: True이면 텍스트/이미지 복사 제한.
        restrict_modify: True이면 수정 제한.
        output_path: 출력 경로. None이면 입력 파일 덮어쓰기.

    Returns:
        보안 적용된 PDF 경로.

    Raises:
        RuntimeError: pikepdf/PyPDF2 모두 사용 불가.
    """
    in_path = Path(pdf_path)
    out_path = Path(output_path) if output_path else in_path

    try:
        import pikepdf

        with pikepdf.open(in_path) as pdf:
            permissions = pikepdf.Permissions(
                print_lowres=not restrict_print,
                print_highres=not restrict_print,
                modify_annotation=not restrict_modify,
                modify_other=not restrict_modify,
                modify_assembly=not restrict_modify,
                extract=not restrict_copy,
                accessibility=True,
            )
            encryption = pikepdf.Encryption(
                user=user_password,
                owner=owner_password,
                R=6,  # AES-256
                allow=permissions,
            )
            pdf.save(str(out_path), encryption=encryption)

        logger.info(f"PDF 보안 적용 완료 (pikepdf): {out_path}")
        return out_path

    except ImportError:
        logger.warning("pikepdf 미설치, PyPDF2로 폴백")

    try:
        from PyPDF2 import PdfReader, PdfWriter

        reader = PdfReader(str(in_path))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        writer.encrypt(
            user_password=user_password,
            owner_password=owner_password,
        )

        with open(out_path, "wb") as f:
            writer.write(f)

        logger.info(f"PDF 보안 적용 완료 (PyPDF2): {out_path}")
        return out_path

    except ImportError:
        raise RuntimeError(
            "PDF 보안 적용을 위해 pikepdf 또는 PyPDF2가 필요합니다. "
            "pip install pikepdf 를 실행하세요."
        )


# ---------------------------------------------------------------------------
# PDF 워터마크 CSS
# ---------------------------------------------------------------------------


def build_watermark_css(
    text: str = "CONFIDENTIAL",
    *,
    opacity: float = 0.2,
    color: str = "#CCCCCC",
    font_size: int = 60,
    position: str = "center_diagonal",
) -> str:
    """PDF 워터마크용 CSS 생성.

    `.slide::after` pseudo-element로 각 슬라이드에 워터마크 표시.

    Args:
        text: 워터마크 텍스트.
        opacity: 불투명도 (0.0~1.0).
        color: 색상 hex.
        font_size: 폰트 크기 (pt).
        position: "center_diagonal" | "top_center" | "bottom_center"

    Returns:
        CSS 문자열.
    """
    if position == "center_diagonal":
        return f"""
        .slide::after {{
            content: "{text}";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: {font_size}pt;
            color: {color};
            opacity: {opacity};
            pointer-events: none;
            z-index: 9999;
            white-space: nowrap;
            font-family: 'Inter', sans-serif;
            font-weight: 800;
            letter-spacing: 0.1em;
        }}
        """
    elif position == "top_center":
        pos_css = "top: 5%;"
    else:
        pos_css = "bottom: 5%;"

    return f"""
    .slide::after {{
        content: "{text}";
        position: absolute;
        {pos_css}
        left: 50%;
        transform: translateX(-50%);
        font-size: {int(font_size * 0.6)}pt;
        color: {color};
        opacity: {opacity};
        pointer-events: none;
        z-index: 9999;
        font-family: 'Inter', sans-serif;
        font-weight: 800;
    }}
    """
