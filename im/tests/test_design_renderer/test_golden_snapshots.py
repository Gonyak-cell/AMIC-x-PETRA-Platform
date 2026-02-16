"""골든 파일 스냅샷 비교 프레임워크 — PPTX 출력 안정성 검증.

> 마지막 수정: 2026-02-11 21:00:00

PPTX 바이너리는 타임스탬프 등 비결정론적 데이터를 포함하므로
구조적 핑거프린트(JSON)를 추출하여 골든 파일과 비교한다.

골든 파일 초기 생성/업데이트:
    pytest tests/test_design_renderer/test_golden_snapshots.py --update-golden -v

일반 비교 실행:
    pytest tests/test_design_renderer/test_golden_snapshots.py -v
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from src.design_renderer.im_document import IMDocumentData
from src.design_renderer.pipeline import IMPipeline, PipelineResult

# ---------------------------------------------------------------------------
# 골든 파일 경로
# ---------------------------------------------------------------------------

GOLDEN_DIR = Path(__file__).parent / "golden"


# ---------------------------------------------------------------------------
# 스냅샷 추출 / 비교 헬퍼
# ---------------------------------------------------------------------------


def _shape_type_label(shape: Any) -> str:
    """shape_type을 사람이 읽기 쉬운 문자열로 변환."""
    try:
        st = shape.shape_type
    except Exception:
        return "unknown"

    mapping = {
        MSO_SHAPE_TYPE.TABLE: "table",
        MSO_SHAPE_TYPE.PICTURE: "picture",
        MSO_SHAPE_TYPE.TEXT_BOX: "text_box",
        MSO_SHAPE_TYPE.AUTO_SHAPE: "auto_shape",
        MSO_SHAPE_TYPE.PLACEHOLDER: "placeholder",
        MSO_SHAPE_TYPE.GROUP: "group",
        MSO_SHAPE_TYPE.FREEFORM: "freeform",
    }
    return mapping.get(st, f"type_{st}")


def extract_pptx_snapshot(
    prs: Presentation,
    *,
    preset: str,
    section_results: list | None = None,
) -> dict[str, Any]:
    """Presentation에서 결정론적 구조 스냅샷을 추출.

    Args:
        prs: python-pptx Presentation 인스턴스.
        preset: 프리셋 이름 ("TITAN", "COVENANT", "FULL").
        section_results: PipelineResult.section_results (섹션별 슬라이드 수 추적용).

    Returns:
        JSON 직렬화 가능한 스냅샷 딕셔너리.
    """
    slides_data: list[dict[str, Any]] = []
    total_text_length = 0
    total_shape_count = 0

    for idx, slide in enumerate(prs.slides):
        texts: list[str] = []
        shape_types: list[str] = []
        has_table = False
        has_picture = False

        for shape in slide.shapes:
            shape_types.append(_shape_type_label(shape))

            if shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                has_table = True
            elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                has_picture = True

            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = para.text.strip()
                    if t:
                        texts.append(t)

        text_length = sum(len(t) for t in texts)
        total_text_length += text_length
        total_shape_count += len(slide.shapes)

        slides_data.append(
            {
                "index": idx,
                "shape_count": len(slide.shapes),
                "text_content": texts,
                "shape_types": sorted(shape_types),
                "has_table": has_table,
                "has_picture": has_picture,
                "text_length": text_length,
            }
        )

    snapshot: dict[str, Any] = {
        "version": 1,
        "preset": preset,
        "total_slides": len(prs.slides),
        "slides": slides_data,
        "total_shape_count": total_shape_count,
        "total_text_length": total_text_length,
    }

    if section_results is not None:
        snapshot["section_slide_counts"] = {
            sr.section_id: sr.pptx_slide_count for sr in section_results
        }

    return snapshot


def load_golden(preset: str, *, golden_dir: Path = GOLDEN_DIR) -> dict[str, Any] | None:
    """골든 파일 로드. 없으면 None.

    Args:
        preset: 프리셋 이름.
        golden_dir: 골든 파일 디렉토리 (테스트용 오버라이드).
    """
    path = golden_dir / f"{preset.lower()}_snapshot.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_golden(
    preset: str,
    snapshot: dict[str, Any],
    *,
    golden_dir: Path = GOLDEN_DIR,
) -> Path:
    """골든 파일 저장.

    Args:
        preset: 프리셋 이름.
        snapshot: 스냅샷 딕셔너리.
        golden_dir: 골든 파일 디렉토리.

    Returns:
        저장된 파일 경로.
    """
    golden_dir.mkdir(parents=True, exist_ok=True)
    path = golden_dir / f"{preset.lower()}_snapshot.json"
    path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def compare_snapshots(
    actual: dict[str, Any],
    golden: dict[str, Any],
) -> list[str]:
    """두 스냅샷 비교. 차이점 리스트 반환 (빈 리스트 = 일치).

    비교 기준:
    - total_slides 일치
    - 각 슬라이드의 shape_count 일치
    - 각 슬라이드의 shape_types 일치
    - 각 슬라이드의 text_content 일치
    - has_table / has_picture 일치
    """
    diffs: list[str] = []

    if actual["total_slides"] != golden["total_slides"]:
        diffs.append(
            f"슬라이드 수: {actual['total_slides']} vs {golden['total_slides']}"
        )
        return diffs

    for a_slide, g_slide in zip(actual["slides"], golden["slides"]):
        idx = a_slide["index"]
        if a_slide["shape_count"] != g_slide["shape_count"]:
            diffs.append(
                f"슬라이드 {idx}: shape_count "
                f"{a_slide['shape_count']} vs {g_slide['shape_count']}"
            )
        if a_slide["shape_types"] != g_slide["shape_types"]:
            diffs.append(f"슬라이드 {idx}: shape_types 불일치")
        if a_slide["text_content"] != g_slide["text_content"]:
            diffs.append(f"슬라이드 {idx}: text_content 불일치")
        if a_slide["has_table"] != g_slide["has_table"]:
            diffs.append(
                f"슬라이드 {idx}: has_table "
                f"{a_slide['has_table']} vs {g_slide['has_table']}"
            )
        if a_slide["has_picture"] != g_slide["has_picture"]:
            diffs.append(
                f"슬라이드 {idx}: has_picture "
                f"{a_slide['has_picture']} vs {g_slide['has_picture']}"
            )

    return diffs


# ---------------------------------------------------------------------------
# TestSnapshotHelpers — 헬퍼 함수 검증
# ---------------------------------------------------------------------------


class TestSnapshotHelpers:
    """스냅샷 헬퍼 함수 단위 테스트."""

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        """저장 → 로드 왕복 일치."""
        snapshot = {
            "version": 1,
            "preset": "TEST",
            "total_slides": 2,
            "slides": [
                {
                    "index": 0,
                    "shape_count": 3,
                    "text_content": ["제목", "본문"],
                    "shape_types": ["text_box", "text_box", "picture"],
                    "has_table": False,
                    "has_picture": True,
                    "text_length": 4,
                },
            ],
            "total_shape_count": 3,
            "total_text_length": 4,
        }

        save_golden("test", snapshot, golden_dir=tmp_path)
        loaded = load_golden("test", golden_dir=tmp_path)

        assert loaded == snapshot

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        """존재하지 않는 골든 파일 로드 시 None 반환."""
        result = load_golden("nonexistent", golden_dir=tmp_path)
        assert result is None

    def test_compare_shape_type_mismatch(self):
        """shape_types 불일치 감지."""
        base = {
            "total_slides": 1,
            "slides": [
                {
                    "index": 0,
                    "shape_count": 2,
                    "text_content": ["텍스트"],
                    "shape_types": ["text_box", "picture"],
                    "has_table": False,
                    "has_picture": True,
                    "text_length": 3,
                },
            ],
        }
        modified = json.loads(json.dumps(base))
        modified["slides"][0]["shape_types"] = ["text_box", "auto_shape"]

        diffs = compare_snapshots(modified, base)
        assert len(diffs) == 1
        assert "shape_types" in diffs[0]

    def test_compare_has_table_mismatch(self):
        """has_table 불일치 감지."""
        base = {
            "total_slides": 1,
            "slides": [
                {
                    "index": 0,
                    "shape_count": 1,
                    "text_content": [],
                    "shape_types": ["table"],
                    "has_table": True,
                    "has_picture": False,
                    "text_length": 0,
                },
            ],
        }
        modified = json.loads(json.dumps(base))
        modified["slides"][0]["has_table"] = False

        diffs = compare_snapshots(modified, base)
        assert len(diffs) == 1
        assert "has_table" in diffs[0]


# ---------------------------------------------------------------------------
# TestSnapshotExtraction — 추출 로직 검증
# ---------------------------------------------------------------------------


class TestSnapshotExtraction:
    """스냅샷 추출 로직 검증."""

    @pytest.fixture
    def _simple_pptx(self) -> Presentation:
        """텍스트박스가 있는 간단한 프레젠테이션."""
        from pptx.util import Inches, Pt

        prs = Presentation()
        layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(layout)
        txbox = slide.shapes.add_textbox(
            Inches(1), Inches(1), Inches(5), Inches(1)
        )
        run = txbox.text_frame.paragraphs[0].add_run()
        run.text = "테스트 텍스트"
        run.font.size = Pt(12)
        return prs

    def test_extract_returns_valid_schema(self, _simple_pptx: Presentation):
        """추출된 스냅샷에 필수 키가 존재."""
        snapshot = extract_pptx_snapshot(_simple_pptx, preset="TEST")

        required_keys = {
            "version",
            "preset",
            "total_slides",
            "slides",
            "total_shape_count",
            "total_text_length",
        }
        assert required_keys.issubset(snapshot.keys())
        assert snapshot["version"] == 1
        assert snapshot["preset"] == "TEST"

    def test_extract_slide_data_complete(self, _simple_pptx: Presentation):
        """각 슬라이드 항목에 필수 필드 존재."""
        snapshot = extract_pptx_snapshot(_simple_pptx, preset="TEST")
        assert len(snapshot["slides"]) > 0

        slide_keys = {
            "index",
            "shape_count",
            "text_content",
            "shape_types",
            "has_table",
            "has_picture",
            "text_length",
        }
        for slide_data in snapshot["slides"]:
            assert slide_keys.issubset(slide_data.keys()), (
                f"슬라이드 {slide_data.get('index', '?')} 필수 키 누락"
            )

    def test_extract_is_deterministic(self, _simple_pptx: Presentation):
        """동일 PPTX 2회 추출 → 동일 결과."""
        snapshot1 = extract_pptx_snapshot(_simple_pptx, preset="TEST")
        snapshot2 = extract_pptx_snapshot(_simple_pptx, preset="TEST")
        assert snapshot1 == snapshot2


# ---------------------------------------------------------------------------
# TestSnapshotComparison — 비교 로직 검증
# ---------------------------------------------------------------------------


class TestSnapshotComparison:
    """스냅샷 비교 로직 검증."""

    def test_identical_snapshots_no_diffs(self):
        """자기 자신 비교 시 diff 없음."""
        snapshot = {
            "total_slides": 1,
            "slides": [
                {
                    "index": 0,
                    "shape_count": 2,
                    "text_content": ["테스트"],
                    "shape_types": ["text_box"],
                    "has_table": False,
                    "has_picture": False,
                    "text_length": 3,
                },
            ],
        }
        diffs = compare_snapshots(snapshot, snapshot)
        assert len(diffs) == 0

    def test_slide_count_mismatch_detected(self):
        """슬라이드 수 차이 감지."""
        a = {"total_slides": 5, "slides": []}
        b = {"total_slides": 7, "slides": []}
        diffs = compare_snapshots(a, b)
        assert len(diffs) == 1
        assert "슬라이드 수" in diffs[0]

    def test_text_content_mismatch_detected(self):
        """텍스트 변경 감지."""
        base = {
            "total_slides": 1,
            "slides": [
                {
                    "index": 0,
                    "shape_count": 1,
                    "text_content": ["원본 텍스트"],
                    "shape_types": ["text_box"],
                    "has_table": False,
                    "has_picture": False,
                    "text_length": 5,
                },
            ],
        }
        modified = json.loads(json.dumps(base))
        modified["slides"][0]["text_content"] = ["변경된 텍스트"]

        diffs = compare_snapshots(modified, base)
        assert len(diffs) == 1
        assert "text_content" in diffs[0]


# ---------------------------------------------------------------------------
# TestGoldenSnapshots — 골든 파일 회귀 테스트
# ---------------------------------------------------------------------------


def _generate_and_snapshot(
    data: IMDocumentData,
    preset: str,
    output_dir: Path,
) -> tuple[dict[str, Any], PipelineResult]:
    """PPTX 생성 후 스냅샷 추출."""
    pipeline = IMPipeline()
    result = pipeline.generate_pptx(
        data, output_path=output_dir / f"{preset.lower()}.pptx"
    )
    prs = Presentation(str(result.pptx_path))
    snapshot = extract_pptx_snapshot(
        prs, preset=preset, section_results=result.section_results
    )
    return snapshot, result


@pytest.mark.golden
class TestGoldenSnapshots:
    """골든 파일 스냅샷 회귀 테스트.

    --update-golden 옵션으로 골든 파일을 생성/업데이트.
    옵션 없이 실행하면 기존 골든 파일과 비교.
    """

    def test_titan_golden_snapshot(
        self,
        titan_data: IMDocumentData,
        tmp_output: Path,
        update_golden: bool,
    ):
        """TITAN 프리셋 골든 스냅샷 비교/업데이트."""
        snapshot, _ = _generate_and_snapshot(titan_data, "TITAN", tmp_output)

        if update_golden:
            path = save_golden("titan", snapshot)
            pytest.skip(f"골든 파일 업데이트 완료: {path}")

        golden = load_golden("titan")
        if golden is None:
            pytest.fail(
                "골든 파일 없음: tests/test_design_renderer/golden/"
                "titan_snapshot.json — --update-golden으로 생성하세요."
            )

        diffs = compare_snapshots(snapshot, golden)
        assert len(diffs) == 0, (
            f"TITAN 골든 불일치 ({len(diffs)}건):\n"
            + "\n".join(f"  - {d}" for d in diffs)
        )

    def test_covenant_golden_snapshot(
        self,
        covenant_data: IMDocumentData,
        tmp_output: Path,
        update_golden: bool,
    ):
        """COVENANT 프리셋 골든 스냅샷 비교/업데이트."""
        snapshot, _ = _generate_and_snapshot(
            covenant_data, "COVENANT", tmp_output
        )

        if update_golden:
            path = save_golden("covenant", snapshot)
            pytest.skip(f"골든 파일 업데이트 완료: {path}")

        golden = load_golden("covenant")
        if golden is None:
            pytest.fail(
                "골든 파일 없음: tests/test_design_renderer/golden/"
                "covenant_snapshot.json — --update-golden으로 생성하세요."
            )

        diffs = compare_snapshots(snapshot, golden)
        assert len(diffs) == 0, (
            f"COVENANT 골든 불일치 ({len(diffs)}건):\n"
            + "\n".join(f"  - {d}" for d in diffs)
        )

    def test_full_golden_snapshot(
        self,
        full_data: IMDocumentData,
        tmp_output: Path,
        update_golden: bool,
    ):
        """FULL 프리셋 골든 스냅샷 비교/업데이트."""
        snapshot, _ = _generate_and_snapshot(full_data, "FULL", tmp_output)

        if update_golden:
            path = save_golden("full", snapshot)
            pytest.skip(f"골든 파일 업데이트 완료: {path}")

        golden = load_golden("full")
        if golden is None:
            pytest.fail(
                "골든 파일 없음: tests/test_design_renderer/golden/"
                "full_snapshot.json — --update-golden으로 생성하세요."
            )

        diffs = compare_snapshots(snapshot, golden)
        assert len(diffs) == 0, (
            f"FULL 골든 불일치 ({len(diffs)}건):\n"
            + "\n".join(f"  - {d}" for d in diffs)
        )

    def test_section_slide_counts_stable(
        self,
        full_data: IMDocumentData,
        tmp_output: Path,
        update_golden: bool,
    ):
        """섹션별 슬라이드 수가 골든 파일과 일치."""
        snapshot, _ = _generate_and_snapshot(full_data, "FULL", tmp_output)
        section_counts = snapshot.get("section_slide_counts", {})
        assert len(section_counts) > 0, "section_slide_counts가 비어있음"

        if update_golden:
            # FULL 골든 파일에 이미 포함됨
            pytest.skip("section_slide_counts는 FULL 골든에 포함")

        golden = load_golden("full")
        if golden is None:
            pytest.skip("FULL 골든 파일 없음")

        golden_counts = golden.get("section_slide_counts", {})
        if not golden_counts:
            pytest.skip("골든 파일에 section_slide_counts 없음")

        mismatched: list[str] = []
        for section_id, count in section_counts.items():
            golden_count = golden_counts.get(section_id)
            if golden_count is not None and count != golden_count:
                mismatched.append(
                    f"{section_id}: {count} vs {golden_count}"
                )

        assert len(mismatched) == 0, (
            f"섹션별 슬라이드 수 불일치:\n"
            + "\n".join(f"  - {m}" for m in mismatched)
        )

    def test_golden_files_exist_without_update_flag(
        self, update_golden: bool
    ):
        """--update-golden 없을 때 골든 파일 3개가 모두 존재."""
        if update_golden:
            pytest.skip("--update-golden 모드에서는 검증 불필요")

        missing: list[str] = []
        for preset in ("titan", "covenant", "full"):
            path = GOLDEN_DIR / f"{preset}_snapshot.json"
            if not path.exists():
                missing.append(str(path))

        if missing:
            pytest.fail(
                f"골든 파일 {len(missing)}개 없음:\n"
                + "\n".join(f"  - {m}" for m in missing)
                + "\n--update-golden 옵션으로 생성하세요."
            )
