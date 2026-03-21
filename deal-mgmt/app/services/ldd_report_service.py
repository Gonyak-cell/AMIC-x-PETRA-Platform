"""LDD(법률실사) 보고서 서비스 — docxtpl 기반 .docx 생성 및 CRUD.

Ralph Loop 2회 적용 워크플로우:
1. create_ldd_report_from_vdr() → Ralph Loop #1 (초안)
2. 사용자 체크리스트 리뷰 (ldd_review_service.py)
3. finalize_ldd_report() → Ralph Loop #2 (최종 Refine)
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError
from app.models.enums import LDDIssueLevel, LDDItemStatus, LDDReportStatus, LDDReportType
from app.models.ldd_evidence_record import LDDEvidenceRecord
from app.models.ldd_report import LDDReport
from app.models.ldd_vdr_reference import LddVdrReference
from app.ralph.generators.ldd.templates import TemplateRegistry
from app.schemas.ldd_report import (
    DEFAULT_LDD_SECTIONS,
    LDDFinalizeRequest,
    LDDReportCreate,
    LDDReportCreateAuto,
    LDDReportCreateFromVdr,
    LDDSectionsUpdate,
)
from app.services.evidence_store_service import (
    build_document_chunk_lookup,
    build_platform_evidence_records,
    replace_platform_evidence_records,
)

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "ldd"
SLOTFILL_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "ldd_slotfill"
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "generated" / "ldd"
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_VERSION = "1.0"


@dataclass
class _NarrativeBlockContext:
    title: str
    content: str


@dataclass
class _NarrativeItemContext:
    item_id: str
    item_name: str
    status: str
    issue_level: str
    blocks: list[_NarrativeBlockContext]


@dataclass
class _NarrativeSectionContext:
    section_title: str
    items: list[_NarrativeItemContext]


def _resolve_sections(deal_type: str, explicit_sections: list | None = None) -> tuple[list[dict], str]:
    """거래유형과 명시적 섹션 데이터로부터 최종 섹션 dict 리스트를 결정한다.

    Returns:
        (sections_data, template_type) 튜플.
        template_type은 적용된 템플릿 식별자 ("DEFAULT" 또는 deal_type 값).
    """
    # 1. 명시적 섹션이 제공되면 최우선 사용
    if explicit_sections:
        return explicit_sections, "CUSTOM"

    # 2. deal_type이 지정되면 TemplateRegistry에서 조회
    if deal_type:
        template_sections = TemplateRegistry.get_sections_dict(deal_type)
        if template_sections:
            return template_sections, deal_type

    # 3. 폴백 — 기존 10개 고정 섹션
    return copy.deepcopy(DEFAULT_LDD_SECTIONS), "DEFAULT"


def _validate_source_dir(source_dir: str) -> None:
    """source_dir가 프로젝트 루트 하위인지 검증한다 (Path Traversal 방어)."""
    try:
        resolved = Path(source_dir).resolve()
        resolved.relative_to(_PROJECT_ROOT)
    except (ValueError, OSError):
        raise ValueError(f"source_dir은 프로젝트 디렉토리 내부여야 합니다: {source_dir}")


# ── 집계 계산 ─────────────────────────────────────────────────────────────────


def _compute_counts(sections: list[dict]) -> dict:
    """섹션 데이터로부터 이슈 카운트를 계산한다."""
    total = issue = red = amber = green = ok = na = pending = rfi = 0

    for section in sections:
        for item in section.get("items", []):
            total += 1
            status = item.get("status", "PENDING")
            level = item.get("issue_level")

            if status == LDDItemStatus.OK:
                ok += 1
            elif status == LDDItemStatus.ISSUE:
                issue += 1
                if level == LDDIssueLevel.CRITICAL:
                    red += 1
                elif level in (LDDIssueLevel.HIGH, LDDIssueLevel.MEDIUM):
                    amber += 1
                elif level == LDDIssueLevel.LOW:
                    green += 1
            elif status == LDDItemStatus.NA:
                na += 1
            else:
                pending += 1

            if item.get("rfi_required"):
                rfi += 1

    return {
        "total_items": total,
        "issue_count": issue,
        "red_count": red,
        "amber_count": amber,
        "green_count": green,
        "ok_count": ok,
        "na_count": na,
        "pending_count": pending,
        "rfi_count": rfi,
    }


def _merge_ai_results(
    sections: list[dict],
    ai_sections: dict,
    *,
    include_ai_meta: bool = True,
    approved_items: set[str] | None = None,
) -> list[dict]:
    """Ralph Loop AI 결과를 기존 섹션에 병합한다.

    Args:
        sections: 기본 섹션 데이터 (변경됨 — in-place)
        ai_sections: AI가 반환한 섹션별 항목 딕셔너리
        include_ai_meta: confidence, evidence_refs 등 AI 메타데이터 포함 여부
        approved_items: 사용자 승인된 item_id 집합. 해당 항목은 AI 결과 대신
                        user_override 값만 적용한다 (finalize 시 사용).
    """
    for section in sections:
        section_type = section["section_type"]
        if section_type not in ai_sections:
            continue
        ai_items = ai_sections[section_type]
        for item in section["items"]:
            item_id = item.get("item_id", "")

            # 승인된 항목: user_override만 적용 (AI 결과 무시)
            if approved_items and item_id in approved_items:
                if item.get("user_override_status"):
                    item["status"] = item["user_override_status"]
                if item.get("user_override_level"):
                    item["issue_level"] = item["user_override_level"]
                continue

            for ai_item in ai_items:
                if ai_item.get("item_id") != item_id:
                    continue
                item["status"] = ai_item.get("status", item.get("status", "PENDING"))
                item["issue_level"] = ai_item.get("issue_level", item.get("issue_level"))
                item["description"] = ai_item.get("description", item.get("description", ""))
                item["deal_impact"] = ai_item.get("deal_impact", item.get("deal_impact", ""))
                item["recommendation"] = ai_item.get("recommendation", item.get("recommendation", ""))
                item["rfi_required"] = ai_item.get("rfi_required", item.get("rfi_required", False))
                item["rfi_number"] = ai_item.get("rfi_number", item.get("rfi_number", ""))
                if include_ai_meta:
                    item["confidence"] = ai_item.get("confidence", item.get("confidence", 0.0))
                    item["evidence_refs"] = ai_item.get("evidence_refs", item.get("evidence_refs", []))
                break
    return sections


def _check_ralph_result(loop_result: object) -> tuple[bool, str]:
    """Ralph Loop 결과에서 실패/critical 신호를 감지한다.

    Returns:
        (ok, reason): ok=True면 정상, False면 실패.
    """
    status = getattr(loop_result, "status", None)
    if status is not None and str(status) == "FAILED":
        errors = getattr(loop_result, "errors", []) or []
        msg = "; ".join(errors[:3]) if errors else "Ralph Loop 실행 실패"
        return False, msg

    critical = getattr(loop_result, "critical_flags", []) or []
    if critical:
        return False, f"Critical 플래그 {len(critical)}건: {'; '.join(critical[:3])}"

    return True, ""


def _check_qa_gate(
    qa_result: dict | None,
    score: float | None,
    min_score: int,
    block_on_critical: bool,
) -> tuple[bool, str]:
    """QA 게이트 — READY 전환 허용 여부 판단.

    NOTE: 점수 척도가 경로마다 다름.
    - 멀티 LLM (draft_score): Stage 7 QA overall_score (1-5)
    - 단일 Ralph (draft_score/final_score): 오케스트레이터 게이트 평균 (0-1)
    향후 통일 필요. 현재는 qa_result=None이면 자동 패스로 안전하게 처리.
    """
    if qa_result is None or score is None:
        return True, ""  # QA 미실행 시 자동 패스

    if score < min_score:
        return False, f"QA 점수 {score:.1f}점이 최소 기준 {min_score}점 미만입니다."

    if block_on_critical:
        issues = qa_result.get("issues") or []
        critical = [i for i in issues if i.get("severity") == "critical"]
        if critical:
            return False, f"QA에서 Critical 이슈 {len(critical)}건이 발견되었습니다."

    return True, ""


def _check_qa_gate_v2(
    qa_result: dict | None,
    score: float | None,
    min_score: int,
    block_on_critical: bool,
) -> tuple[bool, str]:
    """Stricter QA gate with source-control hard blockers."""
    if qa_result is None or score is None:
        return True, ""

    if score < min_score:
        return False, f"QA score {score:.1f} is below the minimum threshold {min_score}."

    issues = qa_result.get("issues") or []
    hard_block_issues = [issue for issue in issues if issue.get("hard_block")]
    if hard_block_issues:
        return False, f"QA hard-block issues found: {len(hard_block_issues)}."

    if block_on_critical:
        critical = [issue for issue in issues if issue.get("severity") == "critical"]
        if critical:
            return False, f"Critical QA issues found: {len(critical)}."

    return True, ""


async def _build_render_narrative_sections(
    report: LDDReport,
    *,
    llm_call=None,
) -> dict[str, list[dict]] | None:
    """렌더링 시 사용할 slot-fill narrative를 조립한다.

    설정상 활성화되어 있으면 sections JSON을 부동문자 bank 기반 block으로 재조합한다.
    실패 시 기존 narrative_sections로 안전하게 폴백한다.
    """
    from app.core.config import settings

    if not settings.LDD_TEMPLATE_SLOTFILL_ENABLED or not report.sections:
        return report.narrative_sections

    try:
        from app.ralph.generators.ldd.slot_fill import LDDTemplateSlotFillEngine

        template_dir = (
            Path(settings.LDD_TEMPLATE_SLOTFILL_DIR) if settings.LDD_TEMPLATE_SLOTFILL_DIR else SLOTFILL_TEMPLATE_DIR
        )
        engine = LDDTemplateSlotFillEngine(
            template_dir,
            llm_call=llm_call,
            use_llm_slots=settings.LDD_TEMPLATE_SLOTFILL_USE_LLM,
        )
        rendered = await engine.build_narrative_sections(
            report,
            industry=report.deal_type or report.template_type or "",
            raw_narrative_sections=report.narrative_sections or {},
        )
        return rendered or report.narrative_sections
    except Exception as exc:
        logger.warning("LDD template slot-fill narrative 조립 실패 — 기존 narrative 폴백: %s", exc)
        return report.narrative_sections


def _compute_risk_colors(sections: list[dict]) -> list[dict]:
    """각 항목의 risk_color를 이슈레벨 기반으로 자동 계산한다."""
    _level_to_color = {
        LDDIssueLevel.CRITICAL: "RED",
        LDDIssueLevel.HIGH: "AMBER",
        LDDIssueLevel.MEDIUM: "AMBER",
        LDDIssueLevel.LOW: "GREEN",
    }
    for section in sections:
        for item in section.get("items", []):
            level = item.get("issue_level")
            if item.get("status") == LDDItemStatus.ISSUE and level:
                item["risk_color"] = _level_to_color.get(level, "")
            else:
                item["risk_color"] = ""
    return sections


# ── docxtpl 렌더링 컨텍스트 빌드 ─────────────────────────────────────────────


def _build_context(
    report: LDDReport,
    *,
    narrative_override: dict[str, list[dict]] | None = None,
) -> dict:
    """docxtpl에 전달할 컨텍스트 딕셔너리를 생성한다."""
    sections = report.sections or []
    if report.report_type == LDDReportType.REDFLAG:
        filtered_sections: list[dict] = []
        for section in sections:
            filtered_items = [
                item
                for item in section.get("items", [])
                if item.get("status") == LDDItemStatus.ISSUE
                and item.get("issue_level") in (
                    LDDIssueLevel.CRITICAL,
                    LDDIssueLevel.HIGH,
                    LDDIssueLevel.MEDIUM,
                )
            ]
            if filtered_items:
                filtered_sections.append(
                    {
                        **section,
                        "items": filtered_items,
                    }
                )
        sections = filtered_sections

    # 전체 이슈 목록 (ISSUE 항목만)
    all_issues = []
    red_issues = []
    sections_with_issues = []

    for section in sections:
        section_title = section.get("title", "")
        sec_issues = []
        for item in section.get("items", []):
            if item.get("status") == LDDItemStatus.ISSUE:
                enriched = {**item, "section_title": section_title}
                all_issues.append(enriched)
                level = item.get("issue_level", "")
                if level in (LDDIssueLevel.CRITICAL, LDDIssueLevel.HIGH, LDDIssueLevel.MEDIUM):
                    sec_issues.append(item)
                    if level == LDDIssueLevel.CRITICAL:
                        red_issues.append(enriched)

        if sec_issues:
            sections_with_issues.append(
                {
                    "title": section_title,
                    "issues": sec_issues,
                }
            )

    ctx = {
        "title": report.title,
        "target_company": report.target_company or "",
        "dd_period": report.dd_period or "",
        "law_firm": report.law_firm or "",
        "prepared_by": report.prepared_by or "",
        "report_date": date.today().strftime("%Y년 %m월 %d일"),
        "total_items": report.total_items,
        "issue_count": report.issue_count,
        "red_count": report.red_count,
        "amber_count": report.amber_count,
        "green_count": report.green_count,
        "ok_count": report.ok_count,
        "na_count": report.na_count,
        "pending_count": report.pending_count,
        "rfi_count": report.rfi_count,
        "sections": sections,
        "all_issues": all_issues,
        "red_issues": red_issues,
        "sections_with_issues": sections_with_issues,
        # VDR 연동 메타데이터
        "vdr_source": report.vdr_source,
        "draft_score": report.draft_score,
        "final_score": report.final_score,
    }

    # 서술(narrative) 데이터가 있으면 narrative_items 컨텍스트 추가
    narrative = narrative_override if narrative_override is not None else report.narrative_sections
    if narrative:
        ctx["narrative_items"] = _build_narrative_items(sections, narrative)

    # 별첨(appendix) 데이터 추가
    if report.appendices and report.appendices.get("tables"):
        ctx["appendix_tables"] = [t for t in report.appendices["tables"] if t.get("row_count", 0) > 0]

    return ctx


def _build_narrative_items(
    sections: list[dict],
    narrative_sections: dict[str, list[dict]],
) -> list[_NarrativeSectionContext]:
    """서술 데이터를 docxtpl 컨텍스트 형식으로 조립한다.

    각 섹션별 항목에 narrative blocks를 매칭하여 반환.

    Returns:
        [
            {
                "section_title": "1. 기업 일반 및 지배구조",
                "items": [
                    {
                        "item_id": "CORP-01",
                        "item_name": "설립/등기/정관 검토",
                        "status": "ISSUE",
                        "issue_level": "HIGH",
                        "blocks": [
                            {"title": "사실관계", "content": "..."},
                            ...
                        ],
                    },
                    ...
                ],
            },
            ...
        ]
    """
    result: list[_NarrativeSectionContext] = []

    for section in sections:
        section_type = section.get("section_type", "")
        section_title = section.get("title", "")
        narrative_items = narrative_sections.get(section_type, [])

        # item_id로 narrative 결과를 매핑
        narrative_by_id: dict[str, dict] = {}
        for nr in narrative_items:
            narrative_by_id[nr.get("item_id", "")] = nr

        items_ctx: list[_NarrativeItemContext] = []
        for item in section.get("items", []):
            item_id = item.get("item_id", "")
            nr = narrative_by_id.get(item_id)

            blocks: list[_NarrativeBlockContext] = []
            if nr and nr.get("blocks"):
                blocks = [
                    _NarrativeBlockContext(
                        title=b.get("title", ""),
                        content=b.get("content", ""),
                    )
                    for b in nr["blocks"]
                    if b.get("content")
                ]

            # 블록이 없으면 체크리스트 데이터를 단일 블록으로 폴백
            if not blocks and item.get("description"):
                blocks = [
                    _NarrativeBlockContext(
                        title="검토 결과",
                        content=item["description"],
                    )
                ]

            if blocks:
                items_ctx.append(
                    _NarrativeItemContext(
                        item_id=item_id,
                        item_name=item.get("name", ""),
                        status=item.get("status", "PENDING"),
                        issue_level=item.get("issue_level", ""),
                        blocks=blocks,
                    )
                )

        if items_ctx:
            result.append(
                _NarrativeSectionContext(
                    section_title=section_title,
                    items=items_ctx,
                )
            )

    return result


# ── CRUD ─────────────────────────────────────────────────────────────────────


def _find_docx_placeholder_hits(docx_path: str) -> list[str]:
    """Inspect a rendered DOCX for unresolved placeholder markers."""
    patterns = (
        "{{",
        "}}",
        "[이곳에 텍스트 입력]",
        "[부문명 기재]",
        "[작성자 기재]",
        "[검토범위 기재]",
        "[프로젝트 코드명]",
    )
    try:
        from docx import Document

        document = Document(docx_path)
    except Exception:
        return []

    hits: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text and any(pattern in text for pattern in patterns):
            hits.append(text[:160])

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                text = cell.text.strip()
                if text and any(pattern in text for pattern in patterns):
                    hits.append(text[:160])

    return hits[:10]


async def list_ldd_reports(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[LDDReport]:
    q = select(LDDReport).where(LDDReport.transaction_id == transaction_id).order_by(LDDReport.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def list_all_ldd_reports(db: AsyncSession) -> list[LDDReport]:
    """모든 거래의 LDD 보고서를 조회한다 (전체 목록)."""
    q = select(LDDReport).order_by(LDDReport.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_ldd_report(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    report_id: uuid.UUID,
) -> LDDReport:
    q = select(LDDReport).where(
        LDDReport.id == report_id,
        LDDReport.transaction_id == transaction_id,
    )
    result = await db.execute(q)
    report = result.scalar_one_or_none()
    if not report:
        raise DocumentNotFoundError("LDD 보고서를 찾을 수 없습니다.")
    return report


async def create_ldd_report(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: LDDReportCreate,
    created_by_email: str | None = None,
) -> LDDReport:
    # 섹션 기본값 적용 — deal_type 우선, 없으면 DEFAULT_LDD_SECTIONS
    explicit = [s.model_dump() for s in body.sections] if body.sections else None
    deal_type = getattr(body, "deal_type", "") or ""
    sections_data, template_type = _resolve_sections(deal_type, explicit)
    sections_data = _compute_risk_colors(sections_data)
    counts = _compute_counts(sections_data)

    report = LDDReport(
        transaction_id=transaction_id,
        report_type=body.report_type,
        deal_type=deal_type or None,
        template_type=template_type,
        title=body.title,
        target_company=body.target_company,
        dd_period=body.dd_period,
        law_firm=body.law_firm,
        prepared_by=body.prepared_by,
        sections=sections_data,
        template_version=TEMPLATE_VERSION,
        created_by_email=created_by_email,
        status=LDDReportStatus.REVIEW,
        review_started_at=datetime.now(UTC),
        **counts,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return report


async def update_ldd_sections(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    report_id: uuid.UUID,
    body: LDDSectionsUpdate,
) -> LDDReport:
    """섹션 데이터를 업데이트하고 보고서를 재렌더링한다."""
    report = await get_ldd_report(db, transaction_id, report_id)

    sections_data = [s.model_dump() for s in body.sections]
    sections_data = _compute_risk_colors(sections_data)
    counts = _compute_counts(sections_data)

    report.sections = sections_data
    for k, v in counts.items():
        setattr(report, k, v)

    # 기존 파일 삭제
    if report.file_path:
        with contextlib.suppress(OSError):
            Path(report.file_path).unlink(missing_ok=True)
    report.file_path = None
    report.file_name = None
    report.file_size_bytes = None

    return await generate_ldd_report(db, report)


async def delete_ldd_report(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    report_id: uuid.UUID,
) -> None:
    report = await get_ldd_report(db, transaction_id, report_id)

    if report.file_path:
        with contextlib.suppress(OSError):
            Path(report.file_path).unlink(missing_ok=True)

    await db.delete(report)
    await db.commit()


# ── docxtpl 렌더링 ────────────────────────────────────────────────────────────


async def generate_ldd_report(
    db: AsyncSession,
    report: LDDReport,
) -> LDDReport:
    """
    asyncio.to_thread을 통해 블로킹 렌더링을 수행한다.

    3가지 경로:
    1. LAW_FIRM → 법무법인 표준 양식 (2단계: 빈 템플릿 생성 → XML 콘텐츠 채우기)
    2. narrative_sections 존재 → 서술형 docxtpl 템플릿
    3. 기본 → 체크리스트형 docxtpl 템플릿
    """
    # ── LAW_FIRM 경로: 2단계 렌더링 ──
    if report.report_type == LDDReportType.LAW_FIRM:
        return await _generate_law_firm_report(db, report)

    # ── 기존 docxtpl 경로 ──
    render_narrative = await _build_render_narrative_sections(report)
    has_narrative = bool(render_narrative)
    prefix = "ldd_narrative_" if has_narrative else "ldd_"
    template_name = f"{prefix}{report.report_type.lower()}_template.docx"
    template_path = TEMPLATE_DIR / template_name

    if not template_path.exists():
        report.status = LDDReportStatus.FAILED
        report.error_message = (
            f"템플릿 파일을 찾을 수 없습니다: {template_name}. "
            "'uv run python scripts/create_ldd_template.py'를 실행하세요."
        )
        await db.commit()
        await db.refresh(report)
        return report

    report_id = report.id
    report_type = report.report_type
    context = _build_context(report, narrative_override=render_narrative)

    def _render() -> tuple[str, str, int]:
        """동기 렌더링 — 별도 스레드에서 실행."""
        from docxtpl import DocxTemplate

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        tpl = DocxTemplate(str(template_path))
        tpl.render(context)
        fname = f"LDD_{report_type}_{report_id}.docx"
        out = OUTPUT_DIR / fname
        tpl.save(str(out))
        return fname, str(out), out.stat().st_size

    # GENERATING 상태로 먼저 저장
    report.status = LDDReportStatus.GENERATING
    await db.commit()

    try:
        fname, fpath, fsize = await asyncio.to_thread(_render)
        placeholder_hits = await asyncio.to_thread(_find_docx_placeholder_hits, fpath)
        if placeholder_hits:
            report.status = LDDReportStatus.FAILED
            report.error_message = f"Rendered DOCX still contains placeholder markers: {' | '.join(placeholder_hits[:3])}"
        else:
            report.status = LDDReportStatus.READY
            report.file_name = fname
            report.file_path = fpath
            report.file_size_bytes = fsize
            report.error_message = None
    except Exception as exc:
        report.status = LDDReportStatus.FAILED
        report.error_message = str(exc)

    await db.commit()
    await db.refresh(report)
    return report


async def _generate_law_firm_report(
    db: AsyncSession,
    report: LDDReport,
) -> LDDReport:
    """법무법인 표준 양식 2단계 렌더링.

    Step 1: LawFirmTemplateGenerator로 빈 템플릿 생성
    Step 2: LawFirmDocxRenderer로 AI 분석 결과 삽입
    """
    from app.ralph.generators.ldd.law_firm_mapper import LawFirmMapper
    from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrativeAdapter
    from app.ralph.generators.ldd.law_firm_renderer import LawFirmDocxRenderer
    from app.ralph.generators.ldd.law_firm_template import LawFirmTemplateGenerator
    from app.ralph.generators.ldd.project_green_style import format_project_green_date

    DIRECT_TEMPLATE = TEMPLATE_DIR / "law_firm_template.docx"
    SOURCE_TEMPLATE = TEMPLATE_DIR / "law_firm_base.docx"

    report.status = LDDReportStatus.GENERATING
    await db.commit()

    try:
        render_narrative = await _build_render_narrative_sections(report)

        def _render_law_firm() -> tuple[str, str, int]:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

            template_path = DIRECT_TEMPLATE if DIRECT_TEMPLATE.exists() else None
            generated_blank_path: Path | None = None

            # Step 1 fallback: blank template가 없으면 기존 생성 경로 유지
            if template_path is None:
                generated_blank_path = OUTPUT_DIR / f"LDD_LAW_FIRM_blank_{report.id}.docx"
                gen = LawFirmTemplateGenerator(SOURCE_TEMPLATE)
                gen.generate_blank_template(
                    output_path=generated_blank_path,
                    project_code=report.target_company or "[프로젝트 코드명]",
                    law_firm_name=report.law_firm or "[법무법인 명칭]",
                    report_date=format_project_green_date(report.created_at or datetime.now(UTC)),
                )
                template_path = generated_blank_path

            # Step 2: 매핑 + 어댑터 + 렌더링
            mapper = LawFirmMapper()
            adapter = LawFirmNarrativeAdapter()

            # DDRL 섹션 → 법무법인 8개 챕터 매핑
            section_results = _sections_to_dict(report.sections or [])
            chapters = mapper.map_sections(
                section_results,
                render_narrative,
            )

            # 3단 서술 변환 (law_firm_sections 우선, 없으면 6블록에서 변환)
            narratives: dict[str, list] = {}
            if render_narrative:
                for ch in chapters:
                    narr_list = []
                    for ddrl_sec in ch.ddrl_sections:
                        if ddrl_sec in render_narrative:
                            narr_list.extend(
                                adapter.convert_chapter(
                                    render_narrative[ddrl_sec],
                                    ch.number,
                                )
                            )
                    narratives[ch.number] = [n.to_dict() if hasattr(n, "to_dict") else n for n in narr_list]
            elif report.law_firm_sections:
                # 이미 3단 구조로 생성된 경우
                narratives = report.law_firm_sections
            elif report.narrative_sections:
                # 6블록 → 3단 변환
                for ch in chapters:
                    narr_list = []
                    for ddrl_sec in ch.ddrl_sections:
                        if ddrl_sec in (report.narrative_sections or {}):
                            narr_list.extend(
                                adapter.convert_chapter(
                                    report.narrative_sections[ddrl_sec],
                                    ch.number,
                                )
                            )
                    narratives[ch.number] = [n.to_dict() if hasattr(n, "to_dict") else n for n in narr_list]

            # Executive Summary 데이터
            exec_summary = None
            if report.qa_result and "summary_rows" in (report.qa_result or {}):
                exec_summary = report.qa_result

            # Step 2: 콘텐츠 채우기
            renderer = LawFirmDocxRenderer()
            fname = f"LDD_LAW_FIRM_{report.id}.docx"
            out = OUTPUT_DIR / fname

            renderer.render(
                template_path=template_path,
                output_path=out,
                report_data={
                    "project_code": report.target_company or "",
                    "law_firm_name": report.law_firm or "",
                    "report_date": format_project_green_date(report.created_at or datetime.now(UTC)),
                    "target_company": report.target_company or "",
                    "report_type_label": "법률실사",
                    "dd_period": report.dd_period or "",
                    "chapters": chapters,
                    "narratives": narratives,
                    "exec_summary": exec_summary,
                    "appendices": report.appendices,
                },
            )

            # fallback으로 생성한 임시 blank만 정리
            if generated_blank_path is not None:
                generated_blank_path.unlink(missing_ok=True)

            return fname, str(out), out.stat().st_size

        fname, fpath, fsize = await asyncio.to_thread(_render_law_firm)
        placeholder_hits = await asyncio.to_thread(_find_docx_placeholder_hits, fpath)
        if placeholder_hits:
            report.status = LDDReportStatus.FAILED
            report.error_message = f"Rendered DOCX still contains placeholder markers: {' | '.join(placeholder_hits[:3])}"
        else:
            report.status = LDDReportStatus.READY
            report.file_name = fname
            report.file_path = fpath
            report.file_size_bytes = fsize
            report.error_message = None

    except Exception as exc:
        logger.exception("법무법인 LDD 렌더링 실패: %s", exc)
        report.status = LDDReportStatus.FAILED
        report.error_message = str(exc)

    await db.commit()
    await db.refresh(report)
    return report


def _sections_to_dict(sections: list[dict]) -> dict[str, list[dict]]:
    """sections JSONB 리스트를 {section_type: items} dict로 변환."""
    result: dict[str, list[dict]] = {}
    for section in sections:
        st = section.get("section_type", "")
        items = section.get("items", [])
        result[st] = items
    return result


async def create_ldd_report_auto(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: LDDReportCreateAuto,
    created_by_email: str | None = None,
) -> LDDReport:
    """Ralph Loop 기반 LDD 보고서 자동 생성.

    1. source_dir 스캔 → 파일 분류
    2. 섹션별 AI 분석 (Ralph Loop)
    3. 결과를 기존 LDDReport에 채워넣기
    4. docxtpl 렌더링
    """
    from app.core.config import settings
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.docx_gate import DOCXProgrammaticGate
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate
    from app.ralph.generators.ldd.section_analyzer import LDDDocumentGenerator, LDDSectionAnalyzer
    from app.ralph.llm_client import RalphLLMClient
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.parsers.file_classifier import parse_and_classify, scan_directory

    # 1. 실사자료 스캔 및 파싱 (경로 검증)
    _validate_source_dir(body.source_dir)
    file_list = scan_directory(body.source_dir)
    if not file_list:
        # 자료 없으면 FAILED 상태로 생성 (빈 보고서 차단)
        sections_data, _template_type = _resolve_sections("")
        counts = _compute_counts(sections_data)
        report = LDDReport(
            transaction_id=transaction_id,
            report_type=body.report_type,
            title=body.title,
            target_company=body.target_company,
            dd_period=body.dd_period,
            law_firm=body.law_firm,
            prepared_by=body.prepared_by,
            sections=sections_data,
            template_version=TEMPLATE_VERSION,
            created_by_email=created_by_email,
            status=LDDReportStatus.FAILED,
            error_message="실사자료 폴더에 분석 가능한 파일이 없습니다.",
            **counts,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    # 2. 파일 파싱 + DDRL 섹션 매핑
    from app.ralph.parsers.base import ParsedFile

    source_map: dict[str, list[ParsedFile]] = {}
    for file_info in file_list:
        parsed = parse_and_classify(file_info["path"])
        for section in parsed.ddrl_sections:
            source_map.setdefault(section, []).append(parsed)

    # 3. LLM 클라이언트 + 학습 패턴 + 분석기 설정
    llm_client = RalphLLMClient.from_settings(settings)
    llm_call = llm_client.call if llm_client.is_available else None

    learned_patterns: list[str] = []
    try:
        from app.ralph.learning.pattern_aggregator import PatternAggregator

        agg = PatternAggregator(db)
        learned_patterns = await agg.get_learned_patterns("LDD")
    except Exception as exc:
        logging.getLogger(__name__).warning("학습 패턴 조회 실패 (무시): %s", exc)

    analyzer = LDDSectionAnalyzer(llm_call=llm_call, learned_patterns=learned_patterns)
    generator = LDDDocumentGenerator(analyzer, copy.deepcopy(DEFAULT_LDD_SECTIONS))
    generator.set_source_map(source_map)

    # 4. 품질 게이트 조립
    gates = [DOCXProgrammaticGate()]
    if llm_call:
        gates.append(LLMJudgeGate(llm_provider=llm_call, doc_type="ldd"))

    # 5. Ralph Loop 실행
    from app.ralph.prd_manager import load_prd

    convergence_config = ConvergenceConfig(
        max_iterations_per_section=body.max_iterations,
        max_cost_usd=body.max_cost_usd,
    )
    prd = load_prd(f"ldd_{body.report_type.lower()}")
    orchestrator = RalphLoopOrchestrator(
        generator=generator,
        gates=gates,
        prd=prd,
        config=LoopConfig(convergence=convergence_config),
    )

    loop_result = await orchestrator.run(source_data={"source_dir": body.source_dir})

    # 5-a. Ralph 실패/critical 신호 차단
    ralph_ok, ralph_reason = _check_ralph_result(loop_result)
    if not ralph_ok:
        sections_data = copy.deepcopy(DEFAULT_LDD_SECTIONS)
        counts = _compute_counts(sections_data)
        report = LDDReport(
            transaction_id=transaction_id,
            report_type=body.report_type,
            title=body.title,
            target_company=body.target_company,
            dd_period=body.dd_period,
            law_firm=body.law_firm,
            prepared_by=body.prepared_by,
            sections=sections_data,
            template_version=TEMPLATE_VERSION,
            created_by_email=created_by_email,
            status=LDDReportStatus.FAILED,
            error_message=ralph_reason,
            **counts,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    # 5-b. 결과를 LDD 섹션 형식으로 변환
    sections_data = copy.deepcopy(DEFAULT_LDD_SECTIONS)
    if loop_result.final_artifact:
        try:
            report_data = json.loads(loop_result.final_artifact)
            ai_sections = report_data.get("sections", {})
            _merge_ai_results(sections_data, ai_sections, include_ai_meta=True)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Ralph Loop 결과 파싱 실패: %s", e)

    sections_data = _compute_risk_colors(sections_data)
    counts = _compute_counts(sections_data)

    # 6. all-PENDING 검증 — AI 분석이 유효한 결과를 산출하지 못한 경우
    all_pending = counts["issue_count"] == 0 and counts["ok_count"] == 0 and counts["na_count"] == 0
    if all_pending:
        report_status = LDDReportStatus.FAILED
        error_msg: str | None = "AI 분석이 완료되었으나 유효한 결과를 산출하지 못했습니다."
    else:
        report_status = LDDReportStatus.DRAFT
        error_msg = None

    # 7. DB 저장
    report = LDDReport(
        transaction_id=transaction_id,
        report_type=body.report_type,
        title=body.title,
        target_company=body.target_company,
        dd_period=body.dd_period,
        law_firm=body.law_firm,
        prepared_by=body.prepared_by,
        sections=sections_data,
        template_version=TEMPLATE_VERSION,
        created_by_email=created_by_email,
        status=report_status,
        error_message=error_msg,
        **counts,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # 8. DOCX 렌더링 (FAILED 상태면 건너뜀)
    if report.status != LDDReportStatus.FAILED:
        report = await generate_ldd_report(db, report)
    return report


# ── VDR 기반 워크플로우 ──────────────────────────────────────────────────────


async def _insert_vdr_references(
    db: AsyncSession,
    report_id: uuid.UUID,
    sections: list[dict],
    vdr_name_to_id: dict[str, uuid.UUID],
) -> None:
    """AI 분석 결과의 evidence_refs를 VDR 문서 UUID로 변환하여 링크 테이블에 저장."""
    import re

    for section in sections:
        section_type = section.get("section_type", "")
        for item in section.get("items", []):
            item_id = item.get("item_id", "")
            for ref in item.get("evidence_refs", []):
                vdr_doc_id: uuid.UUID | None = None

                # [VDR:uuid]filename 형식에서 UUID 추출
                match = re.match(r"\[VDR:([0-9a-f-]{36})\]", ref)
                if match:
                    with contextlib.suppress(ValueError):
                        vdr_doc_id = uuid.UUID(match.group(1))

                # UUID 못 찾으면 파일명으로 매칭
                if not vdr_doc_id:
                    vdr_doc_id = vdr_name_to_id.get(ref)

                # 부분 매칭 시도 (파일명 일부 일치)
                if not vdr_doc_id:
                    for name, vid in vdr_name_to_id.items():
                        if ref in name or name in ref:
                            vdr_doc_id = vid
                            break

                if vdr_doc_id:
                    link = LddVdrReference(
                        ldd_report_id=report_id,
                        item_id=item_id,
                        vdr_document_id=vdr_doc_id,
                        section_type=section_type,
                        relevance_score=item.get("confidence", 0.0),
                        evidence_snippet=item.get("description", "")[:500] if item.get("description") else None,
                    )
                    db.add(link)

    await db.flush()


def _build_vdr_name_lookup(source_files: list) -> dict[str, uuid.UUID]:
    """VDR 파일명 및 prefixed ref → VDR UUID 역매핑."""
    vdr_name_to_id: dict[str, uuid.UUID] = {}
    for vsf in source_files:
        vdr_name_to_id[vsf.original_name] = vsf.vdr_document_id
        vdr_name_to_id[f"[VDR:{vsf.vdr_document_id}]{vsf.original_name}"] = vsf.vdr_document_id
    return vdr_name_to_id


def _build_parsed_source_map(vdr_source_map: dict[str, list]) -> dict[str, list]:
    """VdrSourceFile source_map을 ParsedFile source_map으로 변환한다."""
    parsed_source_map: dict[str, list] = {}
    for section_type, vsf_list in vdr_source_map.items():
        parsed_list = []
        for vsf in vsf_list:
            parsed = copy.copy(vsf.parsed)
            parsed.source_path = f"[VDR:{vsf.vdr_document_id}]{vsf.original_name}"
            parsed_list.append(parsed)
        parsed_source_map[section_type] = parsed_list
    return parsed_source_map


async def _prepare_ldd_vdr_inputs(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    source_files: list,
    *,
    min_common_confidence: float,
) -> tuple[list, list, dict[str, Any], dict[str, list], dict[str, uuid.UUID]]:
    """Route VDR sources by workstream and build LDD-only parsed source inputs."""
    from app.services.ldd_source_controls import filter_ldd_relevant_sources, route_vdr_sources_for_ldd
    from app.services.text_extraction_service import build_source_map
    from app.services.vdr_routing_service import get_routing_override_map

    routing_overrides = await get_routing_override_map(
        db,
        transaction_id,
        document_ids=[source.vdr_document_id for source in source_files],
    )
    routed_sources, source_routing = route_vdr_sources_for_ldd(
        source_files,
        min_common_confidence=min_common_confidence,
        routing_overrides=routing_overrides,
    )
    ldd_sources = filter_ldd_relevant_sources(routed_sources)
    parsed_source_map: dict[str, list] = {}
    if ldd_sources:
        parsed_source_map = _build_parsed_source_map(build_source_map(ldd_sources))
    return routed_sources, ldd_sources, source_routing, parsed_source_map, _build_vdr_name_lookup(source_files)


async def _persist_ldd_evidence_records(
    db: AsyncSession,
    report: LDDReport,
    evidence_records: list[dict[str, Any]],
) -> None:
    chunk_lookup = await build_document_chunk_lookup(
        db,
        vdr_document_ids=[
            uuid.UUID(str(record["vdr_document_id"]))
            for record in evidence_records
            if record.get("vdr_document_id")
        ],
    )
    platform_records = build_platform_evidence_records(
        transaction_id=report.transaction_id,
        artifact_type="LDD_REPORT",
        artifact_id=report.id,
        workstream="LDD",
        source_records=evidence_records,
        document_chunk_lookup=chunk_lookup,
    )

    await db.execute(delete(LDDEvidenceRecord).where(LDDEvidenceRecord.ldd_report_id == report.id))
    await replace_platform_evidence_records(
        db,
        artifact_type="LDD_REPORT",
        artifact_id=report.id,
        records=platform_records,
    )
    for record in evidence_records:
        payload = dict(record)
        vdr_document_id = payload.get("vdr_document_id")
        transaction_id = payload.get("transaction_id")
        payload["ldd_report_id"] = uuid.UUID(str(payload["ldd_report_id"]))
        payload["transaction_id"] = uuid.UUID(str(transaction_id)) if transaction_id else None
        payload["vdr_document_id"] = uuid.UUID(str(vdr_document_id)) if vdr_document_id else None
        db.add(LDDEvidenceRecord(**payload))
    await db.flush()


async def _apply_ldd_source_controls(
    db: AsyncSession,
    report: LDDReport,
    sections: list[dict],
    routed_sources: list,
    source_routing: dict[str, Any],
    qa_result: dict[str, Any] | None,
    *,
    analysis_phase: str,
) -> dict[str, Any]:
    """Persist routing/evidence traceability and merge source-control QA into qa_result."""
    from app.services.ldd_source_controls import (
        build_ldd_evidence_ledger,
        build_ldd_evidence_records,
        build_ldd_source_control_qa,
        merge_source_control_qa,
    )

    evidence_ledger = build_ldd_evidence_ledger(sections, routed_sources)
    evidence_records = build_ldd_evidence_records(
        transaction_id=str(report.transaction_id),
        report_id=str(report.id),
        evidence_ledger=evidence_ledger,
        analysis_phase=analysis_phase,
    )
    source_control_qa = build_ldd_source_control_qa(
        source_routing,
        evidence_ledger,
        sections=sections,
    )

    report.source_routing = source_routing
    report.evidence_ledger = evidence_ledger
    merged_qa = merge_source_control_qa(qa_result, source_control_qa)
    report.qa_result = merged_qa
    await _persist_ldd_evidence_records(db, report, evidence_records)
    return merged_qa


async def create_ldd_report_from_vdr(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: LDDReportCreateFromVdr,
    created_by_email: str | None = None,
) -> LDDReport:
    """Ralph Loop #1: VDR 문서 기반 초안 보고서 생성.

    1. LDDReport 생성 (status=ANALYZING)
    2. VDR 문서 텍스트 추출 (캐시 활용)
    3. 섹션별 소스 매핑
    4. Ralph Loop #1 실행
    5. 결과 → sections JSONB 매핑
    6. evidence_refs → VDR 참조 링크 생성
    7. 상태 → REVIEW
    """
    from app.core.config import settings
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.docx_gate import DOCXProgrammaticGate
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate
    from app.ralph.generators.ldd.section_analyzer import LDDDocumentGenerator, LDDSectionAnalyzer
    from app.ralph.llm_client import RalphLLMClient
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd
    from app.services.text_extraction_service import TextExtractionService

    now = datetime.now(UTC)

    # 1. LDDReport 레코드 생성 — deal_type 기반 템플릿 선택
    deal_type = body.deal_type or ""
    sections_data, template_type = _resolve_sections(deal_type)
    counts = _compute_counts(sections_data)

    report = LDDReport(
        transaction_id=transaction_id,
        report_type=body.report_type,
        deal_type=deal_type or None,
        template_type=template_type,
        title=body.title,
        target_company=body.target_company,
        dd_period=body.dd_period,
        law_firm=body.law_firm,
        prepared_by=body.prepared_by,
        sections=sections_data,
        template_version=TEMPLATE_VERSION,
        created_by_email=created_by_email,
        status=LDDReportStatus.ANALYZING,
        vdr_source=True,
        analysis_started_at=now,
        **counts,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    try:
        # 2. VDR 문서 텍스트 추출
        extractor = TextExtractionService()
        source_files = await extractor.extract_from_vdr_documents(
            db,
            transaction_id,
            folder_ids=body.folder_ids,
        )

        if not source_files:
            report.status = LDDReportStatus.FAILED
            report.error_message = "VDR에 분석 가능한 문서가 없습니다. 문서 업로드 후 재시도하세요."
            report.analysis_completed_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(report)
            return report

        routed_sources, ldd_source_files, source_routing, parsed_source_map, vdr_name_to_id = (
            await _prepare_ldd_vdr_inputs(
                db,
                transaction_id,
                source_files,
                min_common_confidence=settings.LDD_ROUTER_MIN_COMMON_CONFIDENCE,
            )
        )
        report.source_routing = source_routing

        if not ldd_source_files:
            report.status = LDDReportStatus.FAILED
            report.error_message = "VDR에 LDD 관련 문서가 없습니다. 폴더 선택 또는 workstream 분류를 확인하세요."
            report.analysis_completed_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(report)
            return report

        # 4. LLM 클라이언트 + 학습 패턴
        llm_client = RalphLLMClient.from_settings(settings)
        llm_call = llm_client.call if llm_client.is_available else None

        learned_patterns: list[str] = []
        try:
            from app.ralph.learning.pattern_aggregator import PatternAggregator

            agg = PatternAggregator(db)
            learned_patterns = await agg.get_learned_patterns("LDD")
        except Exception as exc:
            logger.warning("학습 패턴 조회 실패 (무시): %s", exc)

        # ── 멀티 LLM 파이프라인 분기 ──
        use_multi_llm = body.use_multi_llm if body.use_multi_llm is not None else settings.LDD_MULTI_LLM_ENABLED

        if use_multi_llm and llm_client.is_available:
            # ★ 멀티 LLM 7단계 파이프라인 ★
            from app.ralph.generators.ldd.pipeline import LDDMultiLLMPipeline
            from app.ralph.generators.ldd.pipeline_config import LDDPipelineConfig
            from app.ralph.routing.ldd_router import LDDModelRouter

            router = LDDModelRouter(llm_client)
            is_law_firm = body.report_type == LDDReportType.LAW_FIRM
            pipeline_config = LDDPipelineConfig(
                stage3_risk_dual=settings.LDD_STAGE3_DUAL_RISK,
                stage4_gap_detection=settings.LDD_STAGE4_GAP_DETECTION,
                stage5_jurisdiction=settings.LDD_STAGE5_JURISDICTION,
                stage6_narrative=settings.LDD_STAGE6_NARRATIVE or is_law_firm,
                stage7_qa=settings.LDD_STAGE7_QA,
                risk_gap_auto_resolve=settings.LDD_RISK_GAP_AUTO_RESOLVE,
                max_cost_usd=settings.LDD_MAX_COST_USD,
                max_iterations=body.draft_max_iterations,
                deal_type=body.deal_type,
                industry=body.industry,
                is_cross_border=body.is_cross_border,
                law_firm_mode=is_law_firm,
            )

            pipeline = LDDMultiLLMPipeline(
                llm_client=llm_client,
                router=router,
                config=pipeline_config,
                source_map=parsed_source_map,
                sections_config=copy.deepcopy(sections_data),
                learned_patterns=learned_patterns,
            )

            # RalphSession 레코드 생성 (멀티 LLM 학습 패턴 축적용)
            from app.models.ralph_session import RalphSession, RalphSessionStatus

            ralph_session = RalphSession(
                id=uuid.uuid4(),
                transaction_id=transaction_id,
                doc_type="LDD",
                status=RalphSessionStatus.PLANNING,
                prd=None,
                config={
                    "pipeline": "multi_llm_7stage",
                    "stage3_risk_dual": pipeline_config.stage3_risk_dual,
                    "stage4_gap_detection": pipeline_config.stage4_gap_detection,
                    "stage5_jurisdiction": pipeline_config.stage5_jurisdiction,
                    "stage7_qa": pipeline_config.stage7_qa,
                    "max_cost_usd": pipeline_config.max_cost_usd,
                },
                learned_patterns=learned_patterns or None,
                created_by_email=created_by_email,
            )
            db.add(ralph_session)
            await db.flush()

            vdr_doc_names = list(vdr_name_to_id.keys())
            pipeline_result = await pipeline.run(vdr_document_names=vdr_doc_names)

            # 파이프라인 실패 체크 — sections이 비어 있으면 실패로 간주
            if not pipeline_result.sections:
                ralph_session.status = RalphSessionStatus.FAILED.value
                ralph_session.error_message = "멀티 LLM 파이프라인이 분석 결과를 산출하지 못했습니다."
                report.status = LDDReportStatus.FAILED
                report.error_message = "AI 분석이 유효한 결과를 산출하지 못했습니다."
                report.analysis_completed_at = datetime.now(UTC)
                await db.commit()
                await db.refresh(report)
                return report

            # RalphSession 결과 업데이트
            ralph_session.status = RalphSessionStatus.COMPLETED.value
            ralph_session.total_cost_usd = pipeline_result.cost_usd
            ralph_session.final_score = (
                pipeline_result.qa_result.get("overall_score") if pipeline_result.qa_result else None
            )
            ralph_session.total_iterations = 1  # 멀티 LLM은 단일 실행

            # 파이프라인 결과 → LDD 섹션 형식 변환
            merged_sections = copy.deepcopy(sections_data)
            if pipeline_result.sections:
                _merge_ai_results(merged_sections, pipeline_result.sections, include_ai_meta=True)
            sections_data = merged_sections

            sections_data = _compute_risk_colors(sections_data)
            counts = _compute_counts(sections_data)

            # VDR 참조 링크 생성
            await _insert_vdr_references(db, report.id, sections_data, vdr_name_to_id)

            # 결과 저장 (멀티 LLM 메타데이터 포함)
            report.sections = sections_data
            for k, v in counts.items():
                setattr(report, k, v)

            report.dual_risk_summary = pipeline_result.dual_risk_summary
            report.gap_detection = pipeline_result.gap_detection
            report.jurisdiction_analysis = pipeline_result.jurisdiction_analysis
            report.narrative_sections = pipeline_result.narrative_sections

            # 법률 인용 검증 결과 추출 (narrative_sections 내부에 포함)
            if pipeline_result.narrative_sections:
                citation_summary: dict = {}
                for sec_type, items in pipeline_result.narrative_sections.items():
                    for item in items:
                        cv = item.get("citation_verification")
                        if cv:
                            citation_summary.setdefault(sec_type, []).append(cv)
                if citation_summary:
                    report.legal_citations = citation_summary

            report.appendices = pipeline_result.appendices
            report.pipeline_stages = pipeline_result.stages
            merged_qa = await _apply_ldd_source_controls(
                db,
                report,
                sections_data,
                routed_sources,
                source_routing,
                pipeline_result.qa_result,
                analysis_phase="DRAFT",
            )
            report.draft_score = merged_qa.get("overall_score") if merged_qa.get("overall_score") is not None else (
                pipeline_result.qa_result.get("overall_score") if pipeline_result.qa_result else None
            )

            # 초안 QA 경고 — 점수가 기준 미달이면 리뷰 시 주의 메시지
            if report.draft_score is not None and report.draft_score < settings.LDD_MIN_DRAFT_SCORE:
                report.error_message = (
                    f"AI 초안 품질 점수가 {report.draft_score:.1f}점입니다 "
                    f"(최소 기준: {settings.LDD_MIN_DRAFT_SCORE}점). 리뷰 시 주의가 필요합니다."
                )

            # ── 법무법인 스타일 후처리 ──
            if is_law_firm and pipeline_result.narrative_sections:
                from app.ralph.generators.ldd.law_firm_mapper import LawFirmMapper
                from app.ralph.generators.ldd.law_firm_narrative_adapter import (
                    LawFirmNarrativeAdapter,
                )

                mapper = LawFirmMapper()
                adapter = LawFirmNarrativeAdapter()

                # DDRL → 8개 목차 매핑
                chapters = mapper.map_sections(
                    pipeline_result.sections,
                    pipeline_result.narrative_sections,
                )
                report.law_firm_toc = mapper.build_toc_data(chapters)

                # 6블록 → 3단 변환
                narratives_by_chapter: dict[str, list] = {}
                for ch in chapters:
                    narr_list = []
                    for ddrl_sec in ch.ddrl_sections:
                        if ddrl_sec in pipeline_result.narrative_sections:
                            narr_list.extend(
                                adapter.convert_chapter(
                                    pipeline_result.narrative_sections[ddrl_sec],
                                    ch.number,
                                )
                            )
                    narratives_by_chapter[ch.number] = narr_list

                report.law_firm_sections = adapter.build_law_firm_sections(
                    narratives_by_chapter,
                )
                report.irl_items = adapter.collect_irl_items(narratives_by_chapter)

            report.status = LDDReportStatus.REVIEW
            report.analysis_completed_at = datetime.now(UTC)
            report.review_started_at = datetime.now(UTC)

        else:
            # ── 기존 단일 LLM 워크플로우 (하위 호환) ──
            analyzer = LDDSectionAnalyzer(llm_call=llm_call, learned_patterns=learned_patterns)
            generator = LDDDocumentGenerator(analyzer, copy.deepcopy(sections_data))
            generator.set_source_map(parsed_source_map)

            # 5. 품질 게이트 + Ralph Loop #1
            gates: list = [DOCXProgrammaticGate()]
            if llm_call:
                gates.append(LLMJudgeGate(llm_provider=llm_call, doc_type="ldd"))

            convergence_config = ConvergenceConfig(
                max_iterations_per_section=body.draft_max_iterations,
                max_cost_usd=body.max_cost_usd * 0.6,  # 전체 예산의 60%를 초안에 배정
            )
            prd_key = f"ldd_{body.report_type.lower()}"  # "FULL" → "ldd_full", "REDFLAG" → "ldd_redflag"
            prd = load_prd(prd_key)

            orchestrator = RalphLoopOrchestrator(
                generator=generator,
                gates=gates,
                prd=prd,
                config=LoopConfig(convergence=convergence_config),
            )

            # 5b. RalphSession 레코드 생성 (학습 패턴 축적용)
            from app.models.ralph_session import RalphSession, RalphSessionStatus

            ralph_session = RalphSession(
                id=uuid.UUID(orchestrator.session_id),
                transaction_id=transaction_id,
                doc_type="LDD",  # get_learned_patterns("LDD") 쿼리와 일치
                status=RalphSessionStatus.PLANNING,
                prd=prd,
                config={
                    "max_iterations": body.draft_max_iterations,
                    "max_cost_usd": body.max_cost_usd * 0.6,
                },
                learned_patterns=learned_patterns or None,
                created_by_email=created_by_email,
            )
            db.add(ralph_session)
            await db.flush()

            loop_result = await orchestrator.run(source_data={"transaction_id": str(transaction_id)})

            # 5c-i. Ralph 실패/critical 신호 차단
            ralph_ok, ralph_reason = _check_ralph_result(loop_result)
            if not ralph_ok:
                ralph_session.status = RalphSessionStatus.FAILED.value
                ralph_session.error_message = ralph_reason
                report.status = LDDReportStatus.FAILED
                report.error_message = ralph_reason
                report.analysis_completed_at = datetime.now(UTC)
                await db.commit()
                await db.refresh(report)
                return report

            # 5c-ii. RalphSession 결과 업데이트
            ralph_session.status = loop_result.status.value
            ralph_session.progress = loop_result.progress
            ralph_session.total_iterations = loop_result.total_iterations
            ralph_session.total_cost_usd = loop_result.total_cost_usd
            ralph_session.final_score = loop_result.final_score
            ralph_session.section_scores = loop_result.section_scores
            ralph_session.critical_flags = loop_result.critical_flags
            ralph_session.error_message = "; ".join(loop_result.errors) if loop_result.errors else None

            # 6. 결과를 LDD 섹션 형식으로 변환
            merged_sections = copy.deepcopy(sections_data)
            if loop_result.final_artifact:
                try:
                    report_data = json.loads(loop_result.final_artifact)
                    ai_sections = report_data.get("sections", {})
                    _merge_ai_results(merged_sections, ai_sections, include_ai_meta=True)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("Ralph Loop #1 결과 파싱 실패: %s", e)
            sections_data = merged_sections

            sections_data = _compute_risk_colors(sections_data)
            counts = _compute_counts(sections_data)

            # 7. VDR 참조 링크 생성
            await _insert_vdr_references(db, report.id, sections_data, vdr_name_to_id)

            # 8. 결과 저장
            report.sections = sections_data
            for k, v in counts.items():
                setattr(report, k, v)

            report.draft_ralph_session_id = uuid.UUID(loop_result.session_id) if loop_result.session_id else None
            report.draft_score = loop_result.final_score
            await _apply_ldd_source_controls(
                db,
                report,
                sections_data,
                routed_sources,
                source_routing,
                report.qa_result,
                analysis_phase="DRAFT",
            )
            report.status = LDDReportStatus.REVIEW
            report.analysis_completed_at = datetime.now(UTC)
            report.review_started_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(report)
        return report

    except Exception as exc:
        logger.exception("LDD 보고서 생성 실패: %s", exc)
        # RalphSession 실패 상태 업데이트 (생성 이후 실패한 경우만)
        try:
            ralph_session.status = RalphSessionStatus.FAILED
            ralph_session.error_message = str(exc)[:500]
        except NameError:
            pass  # ralph_session 또는 멀티 LLM 모드에서 실패한 경우
        report.status = LDDReportStatus.FAILED
        report.error_message = str(exc)
        report.analysis_completed_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(report)
        return report


async def finalize_ldd_report(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    report_id: uuid.UUID,
    body: LDDFinalizeRequest,
) -> LDDReport:
    """Ralph Loop #2: 사용자 피드백 반영 최종 보고서 Refine.

    1. 상태 검증 (REVIEW만 허용)
    2. 사용자 피드백 수집
    3. Ralph Loop #2 (승인 항목 스킵, 반려/수정 항목만 재분석)
    4. DOCX 렌더링
    5. 상태 → READY
    """
    from app.core.config import settings
    from app.core.exceptions import WorkflowError
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.docx_gate import DOCXProgrammaticGate
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate
    from app.ralph.generators.ldd.finalize_generator import LDDFinalizeGenerator
    from app.ralph.generators.ldd.section_analyzer import LDDSectionAnalyzer
    from app.ralph.llm_client import RalphLLMClient
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd
    from app.services.text_extraction_service import TextExtractionService

    report = await get_ldd_report(db, transaction_id, report_id)

    if report.status != LDDReportStatus.REVIEW:
        raise WorkflowError(f"최종 확정은 REVIEW 상태에서만 가능합니다 (현재: {report.status})")

    report.status = LDDReportStatus.FINALIZING
    report.finalize_started_at = datetime.now(UTC)
    await db.commit()

    try:
        # 1. 사용자 피드백 수집
        sections = copy.deepcopy(report.sections or [])
        user_feedback: dict[str, str] = {}
        approved_items: set[str] = set()

        for section in sections:
            for item in section.get("items", []):
                item_id = item.get("item_id", "")
                if item.get("user_approved") is True:
                    approved_items.add(item_id)
                elif item.get("user_approved") is False:
                    parts = []
                    if item.get("user_comment"):
                        parts.append(f"사용자 피드백: {item['user_comment']}")
                    if item.get("user_override_status"):
                        parts.append(f"사용자가 status를 {item['user_override_status']}로 변경 요청")
                    if item.get("user_override_level"):
                        parts.append(f"사용자가 issue_level을 {item['user_override_level']}로 변경 요청")
                    user_feedback[item_id] = "; ".join(parts) if parts else "사용자 반려 — 재분석 필요"

        # 2. VDR 소스 재로딩 (VDR 기반인 경우)
        parsed_source_map: dict[str, list] = {}
        routed_sources: list = []
        source_routing = report.source_routing or {}
        if report.vdr_source:
            extractor = TextExtractionService()
            source_files = await extractor.extract_from_vdr_documents(db, transaction_id)
            if source_files:
                routed_sources, ldd_source_files, source_routing, parsed_source_map, _vdr_name_to_id = (
                    await _prepare_ldd_vdr_inputs(
                        db,
                        transaction_id,
                        source_files,
                        min_common_confidence=settings.LDD_ROUTER_MIN_COMMON_CONFIDENCE,
                    )
                )
                report.source_routing = source_routing
                if report.vdr_source and not ldd_source_files:
                    report.status = LDDReportStatus.REVIEW
                    report.error_message = "LDD 관련 VDR 문서가 식별되지 않아 최종 확정을 진행할 수 없습니다."
                    report.review_started_at = datetime.now(UTC)
                    await db.commit()
                    await db.refresh(report)
                    return report

        # 3. LLM 클라이언트
        llm_client = RalphLLMClient.from_settings(settings)
        llm_call = llm_client.call if llm_client.is_available else None

        learned_patterns: list[str] = []
        try:
            from app.ralph.learning.pattern_aggregator import PatternAggregator

            agg = PatternAggregator(db)
            learned_patterns = await agg.get_learned_patterns("LDD")
        except Exception as exc:
            logger.warning("학습 패턴 조회 실패 (무시): %s", exc)

        analyzer = LDDSectionAnalyzer(llm_call=llm_call, learned_patterns=learned_patterns)

        # 4. LDDFinalizeGenerator (승인 항목 스킵)
        generator = LDDFinalizeGenerator(
            analyzer=analyzer,
            sections_config=sections,
            user_feedback=user_feedback,
            approved_items=approved_items,
        )
        generator.set_source_map(parsed_source_map)

        # 5. 품질 게이트 + Ralph Loop #2
        # user_reviews: 반려된 항목 정보를 게이트에 전달하여 반영 검증
        user_reviews = {item_id: {"approved": False, "feedback": fb} for item_id, fb in user_feedback.items()}
        for item_id in approved_items:
            if item_id not in user_reviews:
                user_reviews[item_id] = {"approved": True, "feedback": ""}

        gates: list = [DOCXProgrammaticGate(user_reviews=user_reviews)]
        if llm_call:
            gates.append(LLMJudgeGate(llm_provider=llm_call, doc_type="ldd"))

        convergence_config = ConvergenceConfig(
            max_iterations_per_section=min(body.max_iterations, 3),
            max_cost_usd=min(body.max_cost_usd, 10.0),
        )
        prd = load_prd(f"ldd_{report.report_type.lower()}")

        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=gates,
            prd=prd,
            config=LoopConfig(convergence=convergence_config),
        )

        # 5b. RalphSession 레코드 생성 (학습 패턴 축적용)
        from app.models.ralph_session import RalphSession, RalphSessionStatus

        ralph_session = RalphSession(
            id=uuid.UUID(orchestrator.session_id),
            transaction_id=transaction_id,
            doc_type="LDD",  # get_learned_patterns("LDD") 쿼리와 일치
            status=RalphSessionStatus.PLANNING,
            prd=prd,
            config={
                "max_iterations": min(body.max_iterations, 3),
                "max_cost_usd": min(body.max_cost_usd, 10.0),
                "pass": "finalize",
            },
            learned_patterns=learned_patterns or None,
            created_by_email=report.created_by_email,
        )
        db.add(ralph_session)
        await db.flush()

        loop_result = await orchestrator.run(source_data={"transaction_id": str(transaction_id)})

        # 5c-i. Ralph Loop #2 실패/critical 신호 차단
        ralph_ok, ralph_reason = _check_ralph_result(loop_result)
        if not ralph_ok:
            ralph_session.status = RalphSessionStatus.FAILED.value
            ralph_session.error_message = ralph_reason
            report.status = LDDReportStatus.FAILED
            report.error_message = f"Ralph Loop #2 실패: {ralph_reason}"
            report.finalize_completed_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(report)
            return report

        # 5c-ii. RalphSession 결과 업데이트
        ralph_session.status = loop_result.status.value
        ralph_session.progress = loop_result.progress
        ralph_session.total_iterations = loop_result.total_iterations
        ralph_session.total_cost_usd = loop_result.total_cost_usd
        ralph_session.final_score = loop_result.final_score
        ralph_session.section_scores = loop_result.section_scores
        ralph_session.critical_flags = loop_result.critical_flags
        ralph_session.error_message = "; ".join(loop_result.errors) if loop_result.errors else None

        # 6. 결과 반영
        if loop_result.final_artifact:
            try:
                report_data = json.loads(loop_result.final_artifact)
                ai_sections = report_data.get("sections", {})
                _merge_ai_results(
                    sections,
                    ai_sections,
                    include_ai_meta=True,
                    approved_items=approved_items,
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Ralph Loop #2 결과 파싱 실패: %s", e)

        sections = _compute_risk_colors(sections)
        counts = _compute_counts(sections)

        report.sections = sections
        for k, v in counts.items():
            setattr(report, k, v)

        report.final_ralph_session_id = uuid.UUID(loop_result.session_id) if loop_result.session_id else None
        report.final_score = loop_result.final_score
        report.finalize_completed_at = datetime.now(UTC)
        if report.vdr_source:
            await _apply_ldd_source_controls(
                db,
                report,
                sections,
                routed_sources,
                source_routing,
                report.qa_result,
                analysis_phase="FINAL",
            )

        # 7. QA 게이트 — 최종 점수가 기준 미달이면 REVIEW로 되돌림
        gate_passed, gate_reason = _check_qa_gate_v2(
            report.qa_result,
            report.final_score,
            settings.LDD_MIN_FINAL_SCORE,
            settings.LDD_QA_CRITICAL_BLOCKS_READY,
        )
        if not gate_passed:
            report.status = LDDReportStatus.REVIEW
            report.error_message = f"QA 게이트 미통과: {gate_reason}"
            report.review_started_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(report)
            return report

        # 8. DOCX 렌더링
        report = await generate_ldd_report(db, report)
        return report

    except Exception as exc:
        logger.exception("Ralph Loop #2 실패: %s", exc)
        # RalphSession 실패 상태 업데이트 (생성 이후 실패한 경우만)
        try:
            ralph_session.status = RalphSessionStatus.FAILED
            ralph_session.error_message = str(exc)[:500]
        except NameError:
            pass  # ralph_session 생성 이전에 실패한 경우
        report.status = LDDReportStatus.FAILED
        report.error_message = str(exc)
        report.finalize_completed_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(report)
        return report


async def regenerate_ldd_report(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    report_id: uuid.UUID,
) -> LDDReport:
    """기존 섹션 데이터로 보고서를 재렌더링한다."""
    report = await get_ldd_report(db, transaction_id, report_id)

    if report.file_path:
        with contextlib.suppress(OSError):
            Path(report.file_path).unlink(missing_ok=True)
    report.file_path = None
    report.file_name = None
    report.file_size_bytes = None

    return await generate_ldd_report(db, report)
