"""모듈 3: 다중 이미지 및 다이어그램 제어.

템플릿 내 Bounding Box 도형의 좌표/크기를 읽어 도형을 삭제한 뒤,
이미지를 Aspect Ratio 보존 + 중앙 맞춤으로 삽입한다.
"""

from __future__ import annotations

import base64
import logging
from io import BytesIO
from typing import Any

from .exceptions import ImagePlacementError
from .shape_finder import find_shape_by_name, find_shapes_by_prefix, get_shape_bounds

logger = logging.getLogger(__name__)


def replace_image_in_placeholder(
    slide: Any,
    shape_name: str,
    image_source: str | bytes,
    *,
    preserve_aspect_ratio: bool = True,
    center_in_bounds: bool = True,
    delete_placeholder: bool = True,
) -> Any:
    """바운딩 박스 도형의 위치에 이미지를 삽입한다.

    Args:
        slide: Slide 인스턴스.
        shape_name: 이미지 바운딩 박스 shape의 name.
        image_source: Base64 인코딩 문자열 또는 raw bytes.
        preserve_aspect_ratio: 이미지 종횡비 보존.
        center_in_bounds: 바운딩 박스 내 중앙 정렬.
        delete_placeholder: 원본 바운딩 박스 도형 삭제.

    Returns:
        삽입된 Picture shape.
    """
    shape = find_shape_by_name(slide, shape_name)
    box_left, box_top, box_width, box_height = get_shape_bounds(shape)

    # 바운딩 박스 도형 삭제
    if delete_placeholder:
        sp = shape._element
        sp.getparent().remove(sp)

    # 이미지 로드
    image_stream = _prepare_image_stream(image_source)

    if preserve_aspect_ratio and center_in_bounds:
        img_left, img_top, img_width, img_height = _fit_and_center(
            box_left, box_top, box_width, box_height, image_stream
        )
    else:
        img_left, img_top = box_left, box_top
        img_width, img_height = box_width, box_height

    # 이미지 삽입
    image_stream.seek(0)
    picture = slide.shapes.add_picture(image_stream, img_left, img_top, img_width, img_height)

    logger.info("이미지 '%s' 삽입 완료 (aspect_ratio=%s)", shape_name, preserve_aspect_ratio)

    return picture


def replace_images_in_grid(
    slide: Any,
    grid_prefix: str,
    image_sources: list[str | bytes],
    *,
    preserve_aspect_ratio: bool = True,
) -> list[Any]:
    """다중 이미지 그리드 교체.

    grid_prefix로 시작하는 모든 플레이스홀더를 찾아 순서대로 교체.
    예: grid_prefix="grid_logo_" → grid_logo_1, grid_logo_2, ...

    Args:
        slide: Slide 인스턴스.
        grid_prefix: 그리드 플레이스홀더 접두사.
        image_sources: 이미지 소스 리스트 (Base64 또는 raw bytes).
        preserve_aspect_ratio: 종횡비 보존.

    Returns:
        삽입된 Picture shape 리스트.
    """
    placeholders = find_shapes_by_prefix(slide, grid_prefix)

    results = []
    for idx, ph in enumerate(placeholders):
        if idx < len(image_sources):
            pic = replace_image_in_placeholder(
                slide,
                ph.name,
                image_sources[idx],
                preserve_aspect_ratio=preserve_aspect_ratio,
            )
            results.append(pic)
        else:
            # 이미지 부족: 플레이스홀더만 삭제
            sp = ph._element
            sp.getparent().remove(sp)

    logger.info(
        "그리드 '%s' 교체 완료: %d/%d 이미지 삽입",
        grid_prefix,
        len(results),
        len(placeholders),
    )

    return results


# ── 내부 헬퍼 ─────────────────────────────────────────────────


def _prepare_image_stream(source: str | bytes) -> BytesIO:
    """이미지 소스를 BytesIO 스트림으로 변환.

    지원 형식:
    - bytes: 그대로 BytesIO 변환
    - str (Base64): base64 디코딩 → BytesIO
    """
    if isinstance(source, bytes):
        return BytesIO(source)

    if isinstance(source, str):
        # Base64 인코딩 감지 (data URI 또는 순수 Base64)
        if source.startswith("data:"):
            # data:image/png;base64,xxxxx
            _, encoded = source.split(",", 1)
            return BytesIO(base64.b64decode(encoded))

        # 순수 Base64 문자열 시도
        try:
            decoded = base64.b64decode(source, validate=True)
            if len(decoded) > 8:  # 최소 이미지 크기
                return BytesIO(decoded)
        except Exception:
            pass

        # 보안: 파일 경로 폴백 제거 (Path Traversal 방어)
        raise ImagePlacementError(
            f"유효하지 않은 이미지 소스입니다. Base64 인코딩 문자열을 전달하세요: {source[:50]}..."
        )

    raise ImagePlacementError(f"지원하지 않는 이미지 소스 타입: {type(source)}")


def _fit_and_center(
    box_left: int,
    box_top: int,
    box_width: int,
    box_height: int,
    image_stream: BytesIO,
) -> tuple[int, int, int, int]:
    """이미지를 바운딩 박스에 맞추고 중앙 정렬.

    Pillow로 이미지 크기를 읽어 aspect ratio를 계산한다.

    Returns:
        (left, top, width, height) EMU 튜플.
    """
    try:
        from PIL import Image

        image_stream.seek(0)
        img = Image.open(image_stream)
        img_w_px, img_h_px = img.size
    except ImportError:
        logger.warning("Pillow 미설치 — 종횡비 보존 불가, 바운딩 박스 크기로 삽입")
        return box_left, box_top, box_width, box_height

    if img_w_px == 0 or img_h_px == 0:
        return box_left, box_top, box_width, box_height

    # fit (contain) 모드: 바운딩 박스 내에 완전히 들어가도록
    scale_w = box_width / img_w_px
    scale_h = box_height / img_h_px
    scale = min(scale_w, scale_h)

    new_width = int(img_w_px * scale)
    new_height = int(img_h_px * scale)

    # 중앙 정렬 오프셋
    offset_left = (box_width - new_width) // 2
    offset_top = (box_height - new_height) // 2

    return (
        box_left + offset_left,
        box_top + offset_top,
        new_width,
        new_height,
    )
