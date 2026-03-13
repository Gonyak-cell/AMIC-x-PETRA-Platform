"""IM 문서 출력 경로 계산 유틸리티."""

from pathlib import Path


def compute_im_output_dir(document_id: str) -> Path:
    """IM 문서 출력 디렉토리를 계산한다."""
    return Path("generated") / "im" / document_id


def compute_im_pptx_path(document_id: str) -> Path:
    """IM PPTX 출력 경로를 계산한다."""
    return compute_im_output_dir(document_id) / f"IM_{document_id}.pptx"
