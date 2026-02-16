"""IM CSS 생성기 — TITAN/COVENANT 레이아웃을 HTML/CSS로 재현.

Radar amic_report.py CSS 패턴을 IM 레이아웃(10.83"×7.5")에 맞게 적용.
모든 색상/폰트/사이즈는 IMDesignTokens에서 동적으로 참조한다.
"""

from __future__ import annotations

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens


def generate_im_css(tokens: IMDesignTokens | None = None) -> str:
    """전체 IM CSS 생성.

    @page, 리셋, 그리드, 슬라이드 클래스, 컴포넌트, 테이블 CSS를 포함한다.

    Args:
        tokens: 디자인 토큰. None이면 AMIC 기본값.

    Returns:
        완전한 CSS 문자열 (HTML <style> 태그 내부에 삽입).
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    parts = [
        _generate_page_rules(tokens),
        _generate_reset_css(),
        _generate_typography_css(tokens),
        _generate_slide_css(tokens),
        _generate_grid_css(),
        _generate_cover_css(tokens),
        _generate_toc_css(tokens),
        _generate_component_css(tokens),
        _generate_table_css(tokens),
        _generate_chart_css(),
        _generate_contact_css(tokens),
        _generate_print_css(),
    ]

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# @page Rules
# ---------------------------------------------------------------------------


def _generate_page_rules(tokens: IMDesignTokens) -> str:
    lay = tokens.layout
    return f"""/* === Page Rules === */
@page {{
    size: {lay.page_width}in {lay.page_height}in;
    margin: 0;
}}"""


# ---------------------------------------------------------------------------
# Reset CSS
# ---------------------------------------------------------------------------


def _generate_reset_css() -> str:
    return """/* === Reset === */
*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html, body {
    width: 100%;
    height: 100%;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}

img {
    max-width: 100%;
    height: auto;
}"""


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------


def _generate_typography_css(tokens: IMDesignTokens) -> str:
    t = tokens.typography
    c = tokens.colors
    f = tokens.font_sizes

    return f"""/* === Typography === */
body {{
    font-family: {t.css_body};
    font-size: {f.body}pt;
    color: {c.text_body};
    line-height: 1.5;
}}

h1, h2, h3, h4 {{
    font-family: {t.css_heading};
    color: {c.primary};
    line-height: 1.2;
}}

.font-mono {{
    font-family: {t.css_mono};
}}

.font-heading {{
    font-family: {t.css_heading};
}}

.text-primary {{ color: {c.primary}; }}
.text-accent {{ color: {c.accent}; }}
.text-body {{ color: {c.text_body}; }}
.text-secondary {{ color: {c.text_secondary}; }}
.text-white {{ color: {c.text_white}; }}
.text-positive {{ color: {c.positive}; }}
.text-negative {{ color: {c.negative}; }}"""


# ---------------------------------------------------------------------------
# Slide Layout
# ---------------------------------------------------------------------------


def _generate_slide_css(tokens: IMDesignTokens) -> str:
    lay = tokens.layout
    c = tokens.colors
    t = tokens.typography
    f = tokens.font_sizes

    return f"""/* === Slide Layout === */
.slide {{
    width: {lay.page_width}in;
    height: {lay.page_height}in;
    position: relative;
    overflow: hidden;
    background: {c.bg_white};
    page-break-inside: avoid;
}}

.slide + .slide {{
    page-break-before: always;
}}

/* Slide Title (MAIN layout idx=11) */
.slide-title {{
    position: absolute;
    left: {lay.margin_left}in;
    top: {lay.margin_top}in;
    width: {lay.content_width}in;
    font-family: {t.css_heading};
    font-weight: 800;
    font-size: {f.slide_title}pt;
    color: {c.primary};
    line-height: 1.2;
}}

/* Summary Text (14pt Bold) */
.summary-text {{
    font-family: {t.css_body};
    font-weight: 700;
    font-size: {f.summary_text}pt;
    color: {c.text_body};
    margin-bottom: 12px;
    line-height: 1.4;
}}

/* Content Area */
.content-area {{
    position: absolute;
    left: {lay.margin_left}in;
    top: {lay.content_top}in;
    width: {lay.content_width}in;
    max-height: {lay.content_height}in;
    overflow: hidden;
}}

/* Slide Footer (idx=12 footnote + idx=13 page number) */
.slide-footer {{
    position: absolute;
    bottom: 0.15in;
    left: {lay.margin_left}in;
    right: {lay.margin_right}in;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}}

.slide-footnote {{
    font-size: {f.footnote}pt;
    color: {c.text_secondary};
    max-width: 80%;
}}

.slide-page-number {{
    font-size: {f.page_number}pt;
    color: {c.text_secondary};
    font-family: {t.css_mono};
    white-space: nowrap;
}}"""


# ---------------------------------------------------------------------------
# 12-Column Grid (Radar 재사용)
# ---------------------------------------------------------------------------


def _generate_grid_css() -> str:
    css = """/* === 12-Column Grid === */
.grid {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 8px;
}

.grid-2col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

.grid-3col {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
}

.grid-4col {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
}
"""

    # col-1 ~ col-12
    for i in range(1, 13):
        css += f".col-{i} {{ grid-column: span {i}; }}\n"

    # row spans
    css += ".row-2 { grid-row: span 2; }\n"
    css += ".row-3 { grid-row: span 3; }\n"

    return css


# ---------------------------------------------------------------------------
# Cover Slide
# ---------------------------------------------------------------------------


def _generate_cover_css(tokens: IMDesignTokens) -> str:
    c = tokens.colors
    t = tokens.typography
    f = tokens.font_sizes

    return f"""/* === Cover Slide === */
.slide-cover {{
    background-size: cover;
    background-position: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
}}

.slide-cover .cover-overlay {{
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(15, 58, 50, 0.75);
    z-index: 1;
}}

.slide-cover .cover-content {{
    position: relative;
    z-index: 2;
    color: {c.text_white};
}}

.cover-title {{
    font-family: {t.css_heading};
    font-weight: 800;
    font-size: {f.cover_title}pt;
    color: {c.text_white};
    margin-bottom: 16px;
}}

.cover-subtitle {{
    font-family: {t.css_body};
    font-size: {f.summary_text}pt;
    color: {c.text_white};
    opacity: 0.9;
}}

.cover-date {{
    font-family: {t.css_mono};
    font-size: {f.body}pt;
    color: {c.text_white};
    opacity: 0.8;
    margin-top: 24px;
}}

.cover-logo {{
    position: absolute;
    bottom: 40px;
    z-index: 2;
}}

.cover-logo img {{
    height: 36px;
}}"""


# ---------------------------------------------------------------------------
# TOC Divider
# ---------------------------------------------------------------------------


def _generate_toc_css(tokens: IMDesignTokens) -> str:
    c = tokens.colors
    t = tokens.typography
    f = tokens.font_sizes

    return f"""/* === TOC Divider === */
.slide-toc {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0 1.5in;
}}

.toc-heading {{
    font-family: {t.css_heading};
    font-weight: 800;
    font-size: {f.toc_heading}pt;
    color: {c.primary};
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 32px;
}}

.toc-list {{
    list-style: none;
    padding: 0;
}}

.toc-item {{
    font-family: {t.css_body};
    font-size: {f.summary_text}pt;
    color: {c.text_secondary};
    padding: 8px 0;
    border-bottom: 1px solid {c.gray_border};
    display: flex;
    align-items: baseline;
    gap: 16px;
}}

.toc-item .toc-number {{
    font-family: {t.css_mono};
    font-weight: 600;
    min-width: 30px;
}}

.toc-item.toc-current {{
    color: {c.primary};
    font-weight: 700;
    text-transform: uppercase;
    border-bottom-color: {c.primary};
}}

.toc-item.toc-current .toc-number {{
    color: {c.accent};
}}"""


# ---------------------------------------------------------------------------
# Component CSS
# ---------------------------------------------------------------------------


def _generate_component_css(tokens: IMDesignTokens) -> str:
    c = tokens.colors
    t = tokens.typography
    f = tokens.font_sizes

    return f"""/* === Components === */

/* Sub-header Bar */
.sub-header-bar {{
    background: {c.primary};
    color: {c.text_white};
    padding: 6px 14px;
    font-family: {t.css_body};
    font-weight: 700;
    font-size: {f.sub_header_bar}pt;
    margin-bottom: 12px;
    border-radius: 2px;
}}

/* KPI Card */
.kpi-card {{
    background: {c.bg_cool_grey};
    border-radius: 6px;
    padding: 16px;
    text-align: center;
}}

.kpi-value {{
    font-family: {t.css_mono};
    font-weight: 700;
    font-size: {f.kpi_value}pt;
    color: {c.primary};
    margin-bottom: 4px;
}}

.kpi-label {{
    font-family: {t.css_body};
    font-size: {f.kpi_label}pt;
    color: {c.text_secondary};
}}

.kpi-change {{
    font-size: {f.small_label}pt;
    margin-top: 4px;
}}

.kpi-change.positive {{ color: {c.positive}; }}
.kpi-change.negative {{ color: {c.negative}; }}

/* Bullet List */
.bullet-list {{
    list-style: none;
    padding-left: 0;
}}

.bullet-list li {{
    position: relative;
    padding-left: 18px;
    margin-bottom: 6px;
    font-size: {f.body}pt;
    line-height: 1.5;
}}

.bullet-list li::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 7px;
    width: 6px;
    height: 6px;
    background: {c.accent};
    border-radius: 50%;
}}

/* Disclaimer */
.disclaimer-text {{
    font-size: {f.footnote}pt;
    color: {c.text_secondary};
    line-height: 1.8;
}}"""


# ---------------------------------------------------------------------------
# Table CSS
# ---------------------------------------------------------------------------


def _generate_table_css(tokens: IMDesignTokens) -> str:
    c = tokens.colors
    t = tokens.typography
    f = tokens.font_sizes
    lay = tokens.layout

    return f"""/* === Financial Table === */
table.financial-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: {f.body}pt;
}}

table.financial-table thead th {{
    background: {c.table_header_bg};
    color: {c.text_white};
    font-weight: 600;
    padding: 6px 8px;
    text-align: center;
    font-size: {f.footnote}pt;
    border: none;
}}

table.financial-table thead th:first-child {{
    text-align: left;
    width: {lay.table_label_col_width}in;
}}

table.financial-table tbody td {{
    padding: 5px 8px;
    border-bottom: 1px solid {c.gray_border};
    font-family: {t.css_mono};
    text-align: right;
}}

table.financial-table tbody td:first-child {{
    font-family: {t.css_body};
    text-align: left;
    font-weight: 500;
    color: {c.text_dark};
}}

table.financial-table tbody tr:nth-child(even) {{
    background: {c.table_alt_row_bg};
}}

table.financial-table tbody tr.total-row {{
    font-weight: 700;
    border-top: 2px solid {c.primary};
    border-bottom: 2px solid {c.primary};
}}

table.financial-table tbody tr.total-row td {{
    color: {c.primary};
}}

/* Generic table */
table.im-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: {f.body}pt;
}}

table.im-table th {{
    background: {c.table_header_bg};
    color: {c.text_white};
    padding: 6px 10px;
    text-align: left;
    font-weight: 600;
}}

table.im-table td {{
    padding: 6px 10px;
    border-bottom: 1px solid {c.gray_border};
}}

table.im-table tr:nth-child(even) {{
    background: {c.table_alt_row_bg};
}}"""


# ---------------------------------------------------------------------------
# Chart CSS
# ---------------------------------------------------------------------------


def _generate_chart_css() -> str:
    return """/* === Chart Container === */
.chart-container {
    text-align: center;
    margin: 12px 0;
}

.chart-container img {
    max-width: 100%;
    height: auto;
}

.timeline-container {
    text-align: center;
    margin: 8px 0;
}

.timeline-container svg {
    max-width: 100%;
    height: auto;
}

.org-chart-container {
    text-align: center;
    margin: 8px 0;
}

.org-chart-container svg {
    max-width: 100%;
    height: auto;
}"""


# ---------------------------------------------------------------------------
# Contact Slide
# ---------------------------------------------------------------------------


def _generate_contact_css(tokens: IMDesignTokens) -> str:
    c = tokens.colors
    t = tokens.typography
    f = tokens.font_sizes

    return f"""/* === Contact Slide === */
.slide-contact {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 1in;
}}

.contact-title {{
    font-family: {t.css_heading};
    font-weight: 800;
    font-size: {f.toc_section_title}pt;
    color: {c.primary};
    margin-bottom: 40px;
}}

.contact-info {{
    font-size: {f.body}pt;
    color: {c.text_body};
    line-height: 2.0;
}}

.contact-name {{
    font-weight: 700;
    font-size: {f.summary_text}pt;
    color: {c.primary};
}}

.contact-role {{
    color: {c.text_secondary};
    font-size: {f.footnote}pt;
}}

.contact-detail {{
    font-family: {t.css_mono};
    font-size: {f.body}pt;
}}"""


# ---------------------------------------------------------------------------
# Print-specific
# ---------------------------------------------------------------------------


def _generate_print_css() -> str:
    return """/* === Print === */
@media print {
    body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    .slide {
        page-break-inside: avoid;
    }

    .slide + .slide {
        page-break-before: always;
    }

    .no-print {
        display: none !important;
    }
}"""
