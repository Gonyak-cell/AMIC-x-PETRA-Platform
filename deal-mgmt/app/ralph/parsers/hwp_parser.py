"""HWP 파서 — pyhwp(hwp5) 기반 한글 문서 파싱.

Fallback: olefile raw text 추출.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.ralph.parsers.base import ParsedFile

logger = logging.getLogger(__name__)


def parse_hwp(file_path: str) -> ParsedFile:
    """HWP 파일을 파싱한다.

    1차: hwp5 (pyhwp) — 텍스트 + 표 추출
    2차: olefile — raw 텍스트만 추출
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".hwpx":
        return _parse_hwpx(file_path)

    # .hwp
    result = _parse_with_hwp5(file_path)
    if result.is_valid:
        return result

    # fallback: olefile
    return _parse_with_olefile(file_path)


def _parse_with_hwp5(file_path: str) -> ParsedFile:
    """pyhwp(hwp5) 기반 파싱."""
    try:
        import hwp5
        from hwp5.hwp5html import open as hwp_open
    except ImportError:
        return ParsedFile(
            source_path=file_path,
            file_type="hwp",
            parse_error="hwp5(pyhwp)가 설치되지 않았습니다 (pip install pyhwp)",
        )

    try:
        # hwp5를 사용해 텍스트 추출
        from hwp5.proc import plaintext

        text_parts: list[str] = []

        with open(file_path, "rb") as f:
            for chunk in plaintext.extract_text(f):
                if isinstance(chunk, str):
                    text_parts.append(chunk)
                elif isinstance(chunk, bytes):
                    text_parts.append(chunk.decode("utf-8", errors="replace"))

        text = "\n".join(text_parts)

        return ParsedFile(
            source_path=file_path,
            file_type="hwp",
            text=text,
            metadata={"parser": "hwp5"},
        )
    except Exception as exc:
        logger.debug("hwp5 파싱 실패, fallback 사용: %s", exc)
        return ParsedFile(
            source_path=file_path,
            file_type="hwp",
            parse_error=f"hwp5 파싱 실패: {exc}",
        )


def _parse_with_olefile(file_path: str) -> ParsedFile:
    """olefile 기반 raw 텍스트 추출 (fallback)."""
    try:
        import olefile
    except ImportError:
        return ParsedFile(
            source_path=file_path,
            file_type="hwp",
            parse_error="olefile이 설치되지 않았습니다 (pip install olefile)",
        )

    try:
        ole = olefile.OleFileIO(file_path)
        try:
            text_parts: list[str] = []

            # HWP의 본문 스트림에서 텍스트 추출
            for stream_name in ole.listdir():
                stream_path = "/".join(stream_name)
                if "BodyText" in stream_path or "Section" in stream_path:
                    data = ole.openstream(stream_name).read()
                    # HWP 본문은 UTF-16LE 인코딩
                    try:
                        text = data.decode("utf-16-le", errors="replace")
                        # 제어 문자 제거
                        cleaned = "".join(c for c in text if c.isprintable() or c in "\n\r\t")
                        if cleaned.strip():
                            text_parts.append(cleaned.strip())
                    except Exception:
                        pass
        finally:
            ole.close()

        if not text_parts:
            return ParsedFile(
                source_path=file_path,
                file_type="hwp",
                parse_error="HWP에서 텍스트를 추출할 수 없습니다",
            )

        return ParsedFile(
            source_path=file_path,
            file_type="hwp",
            text="\n".join(text_parts),
            metadata={"parser": "olefile"},
        )
    except Exception as exc:
        return ParsedFile(
            source_path=file_path,
            file_type="hwp",
            parse_error=f"olefile 파싱 실패: {exc}",
        )


def _parse_hwpx(file_path: str) -> ParsedFile:
    """HWPX (OOXML 기반) 파싱 — ZIP 내부 XML 추출."""
    import xml.etree.ElementTree as ET
    import zipfile

    try:
        text_parts: list[str] = []

        with zipfile.ZipFile(file_path, "r") as zf:
            for name in zf.namelist():
                if "section" in name.lower() and name.endswith(".xml"):
                    with zf.open(name) as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        # 모든 텍스트 노드 추출
                        for elem in root.iter():
                            if elem.text and elem.text.strip():
                                text_parts.append(elem.text.strip())

        return ParsedFile(
            source_path=file_path,
            file_type="hwp",
            text="\n".join(text_parts),
            metadata={"parser": "hwpx_zip"},
        )
    except Exception as exc:
        return ParsedFile(
            source_path=file_path,
            file_type="hwp",
            parse_error=f"HWPX 파싱 실패: {exc}",
        )
