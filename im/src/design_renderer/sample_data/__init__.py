"""IM 실물 수준 샘플 데이터 — 100% 완성된 IMDocumentData 제공.

Phase 2~4에서 IM/TM/DM 각각에 대해 완전한 콘텐츠를 구축한다.
"""

from .dm_full import get_full_dm_data
from .im_full import get_full_im_data
from .tm_full import get_full_tm_data

__all__ = [
    "get_full_dm_data",
    "get_full_im_data",
    "get_full_tm_data",
]
