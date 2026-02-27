"""모듈 4: 텍스트 타임라인 및 동적 텍스트 블록 제어.

text_frame에 접근하여 배열 텍스트를 순차 교체하되,
기존 Run 객체의 서식(폰트, Bold, 색상)을 파괴하지 않고 보존한다.
"""

from __future__ import annotations

import logging
from typing import Any

from .exceptions import TextShapeError
from .shape_finder import find_shape_by_name, find_shapes_by_prefix

logger = logging.getLogger(__name__)


def replace_text_preserving_format(
    slide: Any,
    shape_name: str,
    texts: list[str],
) -> Any:
    """기존 텍스트 shape의 내용을 교체하되 Run 서식을 보존한다.

    paragraph 단위로 texts 배열을 순서대로 매핑한다.
    texts가 기존 paragraph 수보다 많으면 새 paragraph을 추가한다.

    Args:
        slide: Slide 인스턴스.
        shape_name: 텍스트 shape의 name.
        texts: 교체할 텍스트 리스트. paragraph 순서로 매핑.

    Returns:
        수정된 shape.
    """
    shape = find_shape_by_name(slide, shape_name)

    if not shape.has_text_frame:
        raise TextShapeError(f"'{shape_name}'에 text_frame이 없습니다.")

    tf = shape.text_frame
    paragraphs = list(tf.paragraphs)

    for idx, text in enumerate(texts):
        if idx < len(paragraphs):
            _replace_paragraph_text(paragraphs[idx], text)
        else:
            p = tf.add_paragraph()
            if paragraphs:
                _copy_paragraph_format(paragraphs[-1], p)
            run = p.add_run()
            run.text = text

    logger.info("텍스트 '%s' 교체 완료: %d항목", shape_name, len(texts))

    return shape


def replace_placeholders_in_text(
    slide: Any,
    shape_name: str,
    replacements: dict[str, str],
) -> Any:
    """텍스트 내 플레이스홀더({{key}})를 값으로 교체한다.

    기존 서식을 완전히 보존하면서 특정 패턴만 교체.

    Args:
        slide: Slide 인스턴스.
        shape_name: shape name.
        replacements: {"company_name": "알파테크", "date": "2026.03"} 등.

    Returns:
        수정된 shape.
    """
    shape = find_shape_by_name(slide, shape_name)

    if not shape.has_text_frame:
        raise TextShapeError(f"'{shape_name}'에 text_frame이 없습니다.")

    replaced_count = 0
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            text = run.text
            for key, value in replacements.items():
                placeholder = "{{" + key + "}}"
                if placeholder in text:
                    text = text.replace(placeholder, value)
                    replaced_count += 1
            run.text = text

    logger.info(
        "플레이스홀더 '%s' 교체 완료: %d건 치환",
        shape_name,
        replaced_count,
    )

    return shape


def replace_timeline_texts(
    slide: Any,
    prefix: str,
    items: list[dict[str, str]],
) -> list[Any]:
    """타임라인 형식의 연속 텍스트 블록을 일괄 교체.

    prefix로 시작하는 shape들을 찾아 순서대로 교체.
    예: prefix="txt_timeline_" → txt_timeline_1, txt_timeline_2, ...

    각 item은 {"title": "2022.Q1", "content": "시리즈A 투자 유치"} 형태.

    Args:
        slide: Slide 인스턴스.
        prefix: shape name 접두사.
        items: [{"title": "...", "content": "..."}, ...]

    Returns:
        수정된 shape 리스트.
    """
    shapes = find_shapes_by_prefix(slide, prefix)

    results = []
    for idx, shape in enumerate(shapes):
        if idx >= len(items):
            break

        if not shape.has_text_frame:
            continue

        item = items[idx]
        tf = shape.text_frame
        paras = list(tf.paragraphs)

        # 첫 번째 paragraph = 제목
        if paras and "title" in item:
            _replace_paragraph_text(paras[0], item["title"])

        # 나머지 paragraphs = 내용
        if len(paras) > 1 and "content" in item:
            _replace_paragraph_text(paras[1], item["content"])
        elif len(paras) == 1 and "content" in item:
            p = tf.add_paragraph()
            if paras:
                _copy_paragraph_format(paras[0], p)
            run = p.add_run()
            run.text = item["content"]

        results.append(shape)

    logger.info(
        "타임라인 '%s' 교체 완료: %d/%d 항목",
        prefix,
        len(results),
        len(items),
    )

    return results


# ── 내부 헬퍼 ─────────────────────────────────────────────────


def _replace_paragraph_text(paragraph: Any, new_text: str) -> None:
    """paragraph 내 텍스트를 교체하되 첫 번째 run의 서식을 보존."""
    runs = list(paragraph.runs)

    if not runs:
        run = paragraph.add_run()
        run.text = new_text
        return

    first_run = runs[0]

    # 서식 저장
    saved_font_name = first_run.font.name
    saved_font_size = first_run.font.size
    saved_font_bold = first_run.font.bold
    saved_font_italic = first_run.font.italic
    saved_font_color = None
    try:
        saved_font_color = first_run.font.color.rgb
    except (AttributeError, TypeError):
        pass

    # 텍스트 교체
    first_run.text = new_text

    # 나머지 run 제거 (lxml)
    p_elem = paragraph._p
    for run in runs[1:]:
        r_elem = run._r
        p_elem.remove(r_elem)

    # 서식 복원
    if saved_font_name:
        first_run.font.name = saved_font_name
    if saved_font_size:
        first_run.font.size = saved_font_size
    if saved_font_bold is not None:
        first_run.font.bold = saved_font_bold
    if saved_font_italic is not None:
        first_run.font.italic = saved_font_italic
    if saved_font_color:
        first_run.font.color.rgb = saved_font_color


def _copy_paragraph_format(source: Any, target: Any) -> None:
    """source paragraph의 alignment/level을 target에 복사."""
    target.alignment = source.alignment
    target.level = source.level
