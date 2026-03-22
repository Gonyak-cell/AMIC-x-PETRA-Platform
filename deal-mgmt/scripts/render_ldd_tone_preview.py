"""Render before/after LDD tone previews for a representative sample deal.

Currently supports a curated Project Elgar sample derived from the local sample
corpus. The script compares the runtime bank in the current working tree
against the previous committed bank from git HEAD.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import difflib
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.enums import LDDIssueLevel, LDDItemStatus, LDDReportType
from app.ralph.generators.ldd.slot_fill import LDDTemplateSlotFillEngine
from app.schemas.ldd_report import DEFAULT_LDD_SECTIONS


def _git_head_text(repo_root: Path, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def _sample_sections_project_elgar() -> list[dict]:
    base = {sec["section_type"]: copy.deepcopy(sec) for sec in DEFAULT_LDD_SECTIONS}
    selected: list[dict] = []

    governance = copy.deepcopy(base["GOVERNANCE"])
    governance["items"] = [item for item in governance["items"] if item["item_id"] in ("CORP-02", "CORP-04")]
    for item in governance["items"]:
        if item["item_id"] == "CORP-02":
            item.update(
                status=LDDItemStatus.PENDING,
                issue_level=None,
                description="제공 자료만으로는 최근 이사회 의사록과 권한위임 구조를 완결적으로 확인하기 어렵습니다.",
                deal_impact="거래 종결 전후 이사회 운영, 승인권한, 후속 PMI 의사결정 구조 확정이 지연될 수 있습니다.",
                recommendation="최신 이사회 의사록, 위임전결규정, 정관 개정 이력을 추가 확보할 필요가 있습니다.",
                evidence_refs=["[Project Elgar] 실사 주요 이슈.pdf p.1"],
                confidence=0.74,
                rfi_required=True,
                rfi_number="ELGAR-GOV-001",
            )
        elif item["item_id"] == "CORP-04":
            item.update(
                status=LDDItemStatus.ISSUE,
                issue_level=LDDIssueLevel.HIGH,
                description="본건 거래 이후 신규 이사 선임 자체를 위해 별도 정관 개정이 필요하지는 않으나, Anchor 및 Tencent의 사전 승인 이슈가 존재합니다.",
                deal_impact="종결 전 투자자 동의 미확보 시 거래 일정과 post-closing 이사회 구성 확정이 지연될 수 있습니다.",
                recommendation="Anchor 및 Tencent 사전 동의 확보, 종결 후 이사회 구성안 및 승인 절차를 사전에 문서화할 필요가 있습니다.",
                evidence_refs=["[Project Elgar] 실사 주요 이슈.pdf p.1"],
                confidence=0.88,
                rfi_required=True,
                rfi_number="ELGAR-GOV-002",
            )
    selected.append(governance)

    capital = copy.deepcopy(base["CAPITAL"])
    capital["items"] = [item for item in capital["items"] if item["item_id"] in ("CAP-03", "CAP-05")]
    for item in capital["items"]:
        if item["item_id"] == "CAP-03":
            item.update(
                status=LDDItemStatus.ISSUE,
                issue_level=LDDIssueLevel.HIGH,
                description="유효한 스톡옵션이 모두 행사될 경우 최대 약 4.02%의 지분 희석이 가능하고, 행사 방식에 따라 약 1.78% 수준까지 달라질 수 있습니다.",
                deal_impact="투자자 지분율, 희석 가정, 가격조정 메커니즘 및 IPO 시점 지분 구조에 직접 영향을 줄 수 있습니다.",
                recommendation="행사가능 수량, IPO 조건부 물량, 자사주 교부·차액정산 가능 물량을 구분한 희석표를 확정할 필요가 있습니다.",
                evidence_refs=["[Project Elgar] 실사 주요 이슈.pdf p.1"],
                confidence=0.90,
                rfi_required=True,
                rfi_number="ELGAR-CAP-001",
            )
        elif item["item_id"] == "CAP-05":
            item.update(
                status=LDDItemStatus.ISSUE,
                issue_level=LDDIssueLevel.CRITICAL,
                description="Tencent SHA 및 Anchor SHA 모두 본건 거래와 신주발행에 대한 사전 동의권을 포함하고 있고, MFN 조항으로 더 유리한 조건이 확장될 가능성도 존재합니다.",
                deal_impact="동의권자 협의 실패 시 거래 종결, 투자조건 정합성, 향후 지배구조 재편과 exit 구조에 직접적인 제약이 발생할 수 있습니다.",
                recommendation="Tencent 및 Anchor waiver 확보, MFN 영향 분석, 가능하다면 단일화된 주주간계약으로 권리관계를 재정비할 필요가 있습니다.",
                evidence_refs=["[Project Elgar] 실사 주요 이슈.pdf p.2"],
                confidence=0.92,
                rfi_required=True,
                rfi_number="ELGAR-CAP-002",
            )
    selected.append(capital)

    contracts = copy.deepcopy(base["CONTRACTS"])
    contracts["items"] = [item for item in contracts["items"] if item["item_id"] in ("CONTRACT-04", "CONTRACT-05")]
    for item in contracts["items"]:
        if item["item_id"] == "CONTRACT-04":
            item.update(
                status=LDDItemStatus.ISSUE,
                issue_level=LDDIssueLevel.CRITICAL,
                description="기존 주주간계약상 본건 거래에 대한 사전 동의권과 IPO 관련 steering committee/control, put option 가능성이 함께 문제될 수 있습니다.",
                deal_impact="종결 조건, 사전 동의 확보 일정, IPO 기반 exit 전략 및 투자자 협상구조 전반에 영향을 줄 수 있습니다.",
                recommendation="CoC·사전동의·IPO 관련 권리·put option·Anchor 구주매출 우선권을 거래문서에서 명시적으로 정리할 필요가 있습니다.",
                evidence_refs=["[Project Elgar] 실사 주요 이슈.pdf p.2"],
                confidence=0.90,
                rfi_required=True,
                rfi_number="ELGAR-CON-001",
            )
        elif item["item_id"] == "CONTRACT-05":
            item.update(
                status=LDDItemStatus.PENDING,
                issue_level=None,
                description="일부 자회사 주주간계약의 별지 및 옵션 조항 원문이 충분히 제공되지 않아 상세 권리구조를 완결적으로 확인하기 어렵습니다.",
                deal_impact="자회사 지분 처분 제한, tag-along/put option 노출, 자회사 차원의 현금유출 가능성 확정이 지연될 수 있습니다.",
                recommendation="스타쉽, 레전더리스, 영화사 월광 등 자회사 주주간계약 원본과 별지, 옵션 행사현황 자료를 추가 확보할 필요가 있습니다.",
                evidence_refs=["[Project Elgar] 실사 주요 이슈.pdf p.3"],
                confidence=0.71,
                rfi_required=True,
                rfi_number="ELGAR-CON-002",
            )
    selected.append(contracts)
    return selected


def _build_report(sample_name: str) -> SimpleNamespace:
    if sample_name != "project-elgar":
        raise ValueError(f"Unsupported sample: {sample_name}")

    return SimpleNamespace(
        title="Project Elgar Tone Preview",
        target_company="Project Elgar 대상회사",
        report_type=LDDReportType.FULL,
        deal_type="STOCK_ACQUISITION",
        template_type="DEFAULT",
        dd_period="2022-08-26 기준",
        law_firm="김·장 법률사무소 샘플 기반",
        vdr_source=True,
        sections=_sample_sections_project_elgar(),
        narrative_sections={},
    )


def _flatten_narrative(narratives: dict[str, list[dict]]) -> str:
    order = ["GOVERNANCE", "CAPITAL", "CONTRACTS"]
    lines: list[str] = []
    for section_type in order:
        items = narratives.get(section_type, [])
        if not items:
            continue
        lines.append(f"# {section_type}")
        for item in items:
            lines.append(f"## {item['item_name']} ({item['item_id']})")
            for block in item["blocks"]:
                lines.append(f"[{block['block_type']}]")
                lines.append(block["content"])
                lines.append("")
    return "\n".join(lines).strip() + "\n"


async def _render(template_dir: Path, sample_name: str) -> dict[str, list[dict]]:
    report = _build_report(sample_name)
    engine = LDDTemplateSlotFillEngine(template_dir)
    return await engine.build_narrative_sections(report)


async def _run(sample_name: str, output_dir: Path) -> None:
    repo_root = ROOT
    project_root = repo_root.parent
    current_template_dir = repo_root / "templates" / "ldd_slotfill"
    output_dir.mkdir(parents=True, exist_ok=True)

    template_files = sorted(path.name for path in current_template_dir.glob("*.yaml"))

    with TemporaryDirectory() as tmp:
        before_dir = Path(tmp)
        for name in template_files:
            rel = f"deal-mgmt/templates/ldd_slotfill/{name}"
            (before_dir / name).write_text(_git_head_text(project_root, rel), encoding="utf-8")

        before = await _render(before_dir, sample_name)
        after = await _render(current_template_dir, sample_name)

    before_text = _flatten_narrative(before)
    after_text = _flatten_narrative(after)
    diff_text = "".join(
        difflib.unified_diff(
            before_text.splitlines(keepends=True),
            after_text.splitlines(keepends=True),
            fromfile="before",
            tofile="after",
        )
    )

    summary = """# Project Elgar Before/After Tone Preview

- Sample source: `[Project Elgar] 실사 주요 이슈.pdf`
- Render basis: actual sample issues manually structured from the extracted sample text
- Sections covered: `GOVERNANCE`, `CAPITAL`, `CONTRACTS`
- Items covered: `6`

## Expected deltas

- 공통 사실관계 문안이 더 구체적인 제출자료/검토범위 표현으로 바뀝니다.
- `PENDING` 항목에는 자료 공백에 대한 공통 안내가 함께 붙습니다.
- `capital/contracts`는 희석·동의권·waiver 관점의 섹션 특화 문안이 강화됩니다.
- `contracts`는 해외 규제 제외 범위 문구가 명시적으로 드러납니다.
"""

    (output_dir / "before.md").write_text(before_text, encoding="utf-8")
    (output_dir / "after.md").write_text(after_text, encoding="utf-8")
    (output_dir / "diff.md").write_text(diff_text, encoding="utf-8")
    (output_dir / "summary.md").write_text(summary, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", default="project-elgar", help="sample preset name")
    parser.add_argument(
        "--output-dir",
        default="generated/ldd_slotfill_preview_project_elgar",
        help="output directory relative to deal-mgmt",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    asyncio.run(_run(args.sample, output_dir))


if __name__ == "__main__":
    main()
