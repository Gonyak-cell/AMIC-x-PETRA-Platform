"""IM doc_type 해석 유틸리티.

im_style 문자열을 Ralph Loop doc_type으로 변환한다.
Celery 태스크에서 분리하여 단위 테스트를 용이하게 한다.
"""

from __future__ import annotations


def resolve_doc_type(im_style: str) -> str:
    """im_style을 Ralph Loop doc_type으로 변환한다.

    Args:
        im_style: "TEASER", "TM", "DM", "FULL" 등.

    Returns:
        "im_teaser", "im_dm", 또는 "im_full".
    """
    style = im_style.upper()
    if style in ("TEASER", "TM"):
        return "im_teaser"
    elif style == "DM":
        return "im_dm"
    else:
        return "im_full"
