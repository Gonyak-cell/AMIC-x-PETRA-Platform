"""AnalysisOrchestrator — VDR 기반 자동 FDD 분석 + 체크리스트 생성.

VDR에 업로드된 파일을 기반으로:
1. 스냅샷 생성
2. QoE / NWC / Net Debt 엔진 실행
3. (선택) 멀티 LLM 교차검증
4. 분석 결과에서 FDD 체크리스트 자동 생성 (18개 카테고리)
5. 체크리스트 항목에 VDR 소스 파일 연결
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.analysis_run import AnalysisRun, AnalysisRunStatus
from app.models.deal import Deal, DealDefinition, DealSnapshot, DefinitionStatus
from app.models.fdd_checklist import (
    ChecklistCategory,
    ChecklistItemStatus,
    ChecklistItemVdrLink,
    ChecklistSeverity,
    ChecklistStatus,
    FddChecklist,
    FddChecklistItem,
)
from app.models.upload import IngestionStatus, UploadFile
from app.models.vdr import VdrFolder, VdrFolderType

logger = get_logger(__name__)


@dataclass
class CrossVerifyConfig:
    """교차검증 설정."""

    review_mode: str = "BLIND"
    qoe_enabled: bool = True
    nwc_enabled: bool = True
    debt_enabled: bool = True
    max_cost_usd: Decimal = Decimal("10.00")


# ── VDR 폴더 타입 → 체크리스트 카테고리 매핑 ────────────────────────────────

_FOLDER_TO_CATEGORIES: dict[VdrFolderType, list[ChecklistCategory]] = {
    VdrFolderType.FINANCIAL_STATEMENTS: [
        ChecklistCategory.REVENUE_RECOGNITION,
        ChecklistCategory.COGS_CLASSIFICATION,
        ChecklistCategory.SGA_ANALYSIS,
        ChecklistCategory.NON_RECURRING_ITEMS,
        ChecklistCategory.RELATED_PARTY_TRANSACTIONS,
        ChecklistCategory.EBITDA_ADJUSTMENTS,
    ],
    VdrFolderType.ACCOUNTS_RECEIVABLE: [
        ChecklistCategory.AR_AGING,
        ChecklistCategory.NWC_CLASSIFICATION,
    ],
    VdrFolderType.ACCOUNTS_PAYABLE: [
        ChecklistCategory.AP_AGING,
        ChecklistCategory.NWC_CLASSIFICATION,
    ],
    VdrFolderType.BANK_DEBT: [
        ChecklistCategory.DEBT_SCHEDULE,
        ChecklistCategory.DEBT_LIKE_ITEMS,
    ],
    VdrFolderType.LEASE: [
        ChecklistCategory.LEASE_OBLIGATIONS,
    ],
    VdrFolderType.OTHERS: [
        ChecklistCategory.TAX_REVIEW,
        ChecklistCategory.CONTINGENT_LIABILITIES,
        ChecklistCategory.OFF_BALANCE_SHEET,
    ],
}


# ── 카테고리별 기본 체크리스트 항목 정의 ──────────────────────────────────────

_CATEGORY_ITEMS: dict[ChecklistCategory, dict] = {
    ChecklistCategory.REVENUE_RECOGNITION: {
        "title": "Revenue Recognition Review",
        "description": "매출인식 기준, 시점, 반복성 분석",
        "severity": ChecklistSeverity.HIGH,
    },
    ChecklistCategory.COGS_CLASSIFICATION: {
        "title": "COGS Classification Review",
        "description": "매출원가 분류 정확성 및 감가상각 배분 확인",
        "severity": ChecklistSeverity.HIGH,
    },
    ChecklistCategory.SGA_ANALYSIS: {
        "title": "SG&A Expense Analysis",
        "description": "판관비 항목별 분석 및 비정상 항목 식별",
        "severity": ChecklistSeverity.MEDIUM,
    },
    ChecklistCategory.NON_RECURRING_ITEMS: {
        "title": "Non-Recurring Items Identification",
        "description": "비경상 항목 식별 및 EBITDA 조정 대상 확인",
        "severity": ChecklistSeverity.HIGH,
    },
    ChecklistCategory.RELATED_PARTY_TRANSACTIONS: {
        "title": "Related Party Transactions",
        "description": "특수관계인 거래 식별 및 시장가 대비 검토",
        "severity": ChecklistSeverity.HIGH,
    },
    ChecklistCategory.EBITDA_ADJUSTMENTS: {
        "title": "EBITDA Adjustment Summary",
        "description": "전체 EBITDA 조정 항목 요약 및 정당성 검토",
        "severity": ChecklistSeverity.HIGH,
    },
    ChecklistCategory.NWC_CLASSIFICATION: {
        "title": "NWC Account Classification",
        "description": "운전자본 항목 분류 (Above/Below Line) 적정성 확인",
        "severity": ChecklistSeverity.MEDIUM,
    },
    ChecklistCategory.AR_AGING: {
        "title": "Accounts Receivable Aging",
        "description": "매출채권 연령 분석 및 회수 가능성 평가",
        "severity": ChecklistSeverity.MEDIUM,
    },
    ChecklistCategory.AP_AGING: {
        "title": "Accounts Payable Aging",
        "description": "매입채무 연령 분석 및 지급 조건 검토",
        "severity": ChecklistSeverity.LOW,
    },
    ChecklistCategory.INVENTORY_ANALYSIS: {
        "title": "Inventory Analysis",
        "description": "재고 평가, 회전율, 진부화 위험 분석",
        "severity": ChecklistSeverity.MEDIUM,
    },
    ChecklistCategory.NWC_SEASONALITY: {
        "title": "NWC Seasonality Analysis",
        "description": "운전자본 계절성 패턴 및 Peg 시나리오 영향 분석",
        "severity": ChecklistSeverity.LOW,
    },
    ChecklistCategory.DEBT_SCHEDULE: {
        "title": "Debt Schedule Review",
        "description": "차입금 명세 및 만기 구조 분석",
        "severity": ChecklistSeverity.HIGH,
    },
    ChecklistCategory.DEBT_LIKE_ITEMS: {
        "title": "Debt-like Items Identification",
        "description": "부채성 항목(연금, 리스 등) 식별 및 조정 대상 확인",
        "severity": ChecklistSeverity.MEDIUM,
    },
    ChecklistCategory.CASH_LIKE_ITEMS: {
        "title": "Cash-like Items Identification",
        "description": "현금성 자산(단기금융상품, 보증금 등) 식별",
        "severity": ChecklistSeverity.MEDIUM,
    },
    ChecklistCategory.LEASE_OBLIGATIONS: {
        "title": "Lease Obligations (IFRS 16)",
        "description": "사용권자산/리스부채 분류 및 Net Debt 반영 여부 결정",
        "severity": ChecklistSeverity.MEDIUM,
    },
    ChecklistCategory.TAX_REVIEW: {
        "title": "Tax Position Review",
        "description": "세무 포지션, 이연법인세, 세무 리스크 검토",
        "severity": ChecklistSeverity.MEDIUM,
    },
    ChecklistCategory.CONTINGENT_LIABILITIES: {
        "title": "Contingent Liabilities",
        "description": "우발부채(소송, 보증, 환경) 식별 및 영향 분석",
        "severity": ChecklistSeverity.HIGH,
    },
    ChecklistCategory.OFF_BALANCE_SHEET: {
        "title": "Off-Balance Sheet Items",
        "description": "부외 항목 식별 (운용리스, 약정, SPV 등)",
        "severity": ChecklistSeverity.MEDIUM,
    },
}


class AnalysisOrchestrator:
    """VDR 기반 자동 FDD 분석을 오케스트레이션한다."""

    def __init__(
        self,
        db: Session,
        cross_verify_enabled: bool = False,
        cross_verify_config: CrossVerifyConfig | None = None,
    ):
        self.db = db
        self.cross_verify_enabled = cross_verify_enabled
        self.cross_verify_config = cross_verify_config or CrossVerifyConfig()

    # ──────────────────────────────────────────────────────────────────────

    def run_analysis(
        self,
        deal_id: uuid.UUID,
        file_ids: list[uuid.UUID] | None = None,
        actor: str = "system",
    ) -> AnalysisRun:
        """전체 자동 분석 파이프라인을 실행한다.

        1. VDR에서 COMPLETED 파일 수집
        2. 스냅샷 생성
        3. QoE / NWC / Net Debt 엔진 실행
        4. 체크리스트 자동 생성
        5. 체크리스트 항목 ↔ VDR 소스 연결

        Args:
            deal_id: 대상 Deal UUID
            file_ids: 분석할 파일 ID 목록 (None이면 VDR 전체)
            actor: 실행자 (이메일 또는 "system")

        Returns:
            생성된 AnalysisRun 레코드
        """
        deal = self.db.get(Deal, deal_id)
        if deal is None:
            raise ValueError(f"Deal {deal_id} not found")

        # 1. AnalysisRun 생성
        run = AnalysisRun(
            deal_id=deal_id,
            trigger="manual" if actor != "system" else "system",
            status=AnalysisRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        self.db.flush()

        try:
            # 2. VDR 파일 수집
            completed_files = self._collect_files(deal_id, file_ids)
            run.input_file_ids = [str(f.id) for f in completed_files]
            run.progress_percent = 10

            if not completed_files:
                logger.warning("No COMPLETED files found for deal %s", deal_id)

            # 3. 스냅샷 생성
            snapshot = self._get_or_create_snapshot(deal_id)
            run.progress_percent = 20

            # 4. 엔진 실행
            qoe_calc = self._run_qoe(deal_id, snapshot.id)
            run.progress_percent = 30

            nwc_calc = self._run_nwc(deal_id, snapshot.id)
            run.progress_percent = 50

            debt_calc = self._run_debt(deal_id, snapshot.id)
            run.progress_percent = 65

            # 4.5. 교차검증 (활성화된 경우)
            cv_results: dict[str, Any] = {}
            if self.cross_verify_enabled:
                cv_results = self._run_cross_verification(
                    deal_id, qoe_calc, nwc_calc, debt_calc,
                    completed_files=completed_files,
                )
                run.cross_verify_summary = cv_results
            run.progress_percent = 80

            # 5. 체크리스트 생성
            checklist = self._build_checklist(
                deal_id=deal_id,
                qoe_calc=qoe_calc,
                nwc_calc=nwc_calc,
                debt_calc=debt_calc,
                completed_files=completed_files,
                actor=actor,
                cv_results=cv_results,
            )
            run.output_checklist_id = checklist.id
            run.progress_percent = 100
            run.status = AnalysisRunStatus.COMPLETED
            run.completed_at = datetime.now(UTC)

            self.db.commit()
            self.db.refresh(run)
            logger.info(
                "Analysis completed for deal %s — checklist %s created with %d items",
                deal_id,
                checklist.id,
                len(checklist.items),
            )
            return run

        except Exception as e:
            run.status = AnalysisRunStatus.FAILED
            run.error_message = str(e)[:2000]
            run.completed_at = datetime.now(UTC)
            self.db.commit()
            logger.error("Analysis failed for deal %s: %s", deal_id, e)
            raise

    # ── Private helpers ──────────────────────────────────────────────────

    def _collect_files(
        self,
        deal_id: uuid.UUID,
        file_ids: list[uuid.UUID] | None,
    ) -> list[UploadFile]:
        """VDR의 COMPLETED 상태 파일들을 수집한다."""
        stmt = select(UploadFile).where(
            UploadFile.deal_id == deal_id,
            UploadFile.status == IngestionStatus.COMPLETED,
        )
        if file_ids:
            stmt = stmt.where(UploadFile.id.in_(file_ids))
        return list(self.db.scalars(stmt).all())

    def _get_or_create_snapshot(self, deal_id: uuid.UUID) -> DealSnapshot:
        """최신 APPROVED DealDefinition 기반 스냅샷을 생성한다."""
        from app.services.snapshot_service import create_snapshot

        latest_def = self.db.scalar(
            select(DealDefinition)
            .where(
                DealDefinition.deal_id == deal_id,
                DealDefinition.status == DefinitionStatus.APPROVED,
            )
            .order_by(DealDefinition.version.desc())
            .limit(1)
        )
        if latest_def is None:
            # APPROVED가 없으면 최신 definition 사용
            latest_def = self.db.scalar(
                select(DealDefinition)
                .where(DealDefinition.deal_id == deal_id)
                .order_by(DealDefinition.version.desc())
                .limit(1)
            )
        if latest_def is None:
            raise ValueError(f"No DealDefinition found for deal {deal_id}")

        return create_snapshot(self.db, deal_id, latest_def.id)

    def _run_qoe(self, deal_id: uuid.UUID, snapshot_id: uuid.UUID):
        """QoE 엔진을 실행한다. 데이터 부족 시 None 반환."""
        try:
            from app.services.qoe.qoe_service import run_qoe_calculation

            return run_qoe_calculation(self.db, deal_id, snapshot_id)
        except Exception as e:
            logger.warning("QoE calculation skipped for deal %s: %s", deal_id, e)
            return None

    def _run_nwc(self, deal_id: uuid.UUID, snapshot_id: uuid.UUID):
        """NWC 엔진을 실행한다. 데이터 부족 시 None 반환."""
        try:
            from app.services.nwc.nwc_service import run_nwc_calculation

            return run_nwc_calculation(
                self.db, deal_id, snapshot_id, peg_method="LTM_AVERAGE"
            )
        except Exception as e:
            logger.warning("NWC calculation skipped for deal %s: %s", deal_id, e)
            return None

    def _run_debt(self, deal_id: uuid.UUID, snapshot_id: uuid.UUID):
        """Net Debt 엔진을 실행한다. 데이터 부족 시 None 반환."""
        try:
            from app.services.debt.debt_service import run_net_debt_calculation

            return run_net_debt_calculation(
                self.db, deal_id, snapshot_id,
                include_lease_liabilities=True,
                include_deferred_revenue=False,
            )
        except Exception as e:
            logger.warning("Debt calculation skipped for deal %s: %s", deal_id, e)
            return None

    def _build_checklist(
        self,
        deal_id: uuid.UUID,
        qoe_calc,
        nwc_calc,
        debt_calc,
        completed_files: list[UploadFile],
        actor: str,
        cv_results: dict[str, Any] | None = None,
    ) -> FddChecklist:
        """분석 결과에서 FDD 체크리스트를 자동 생성한다."""
        # 기존 체크리스트 버전 확인
        latest_version = self.db.scalar(
            select(FddChecklist.version)
            .where(FddChecklist.deal_id == deal_id)
            .order_by(FddChecklist.version.desc())
            .limit(1)
        )
        next_version = (latest_version or 0) + 1

        checklist = FddChecklist(
            deal_id=deal_id,
            version=next_version,
            status=ChecklistStatus.PENDING_REVIEW,
            created_by=actor,
        )
        self.db.add(checklist)
        self.db.flush()

        # 파일 → 폴더 타입 매핑
        file_folder_map = self._build_file_folder_map(completed_files)

        # 카테고리별 항목 생성
        order = 0
        for category in ChecklistCategory:
            item_def = _CATEGORY_ITEMS[category]
            item = FddChecklistItem(
                checklist_id=checklist.id,
                category=category,
                order_index=order,
                title=item_def["title"],
                description=item_def["description"],
                severity=item_def["severity"],
            )

            # 엔진 결과에서 자동 finding 채우기
            self._populate_auto_finding(item, category, qoe_calc, nwc_calc, debt_calc)

            self.db.add(item)
            self.db.flush()

            # VDR 소스 연결
            self._link_vdr_sources(item, category, file_folder_map)

            order += 1

        # 교차검증 결과 반영
        if cv_results:
            self._apply_cv_flags(checklist, cv_results)

        self.db.flush()
        self.db.refresh(checklist)
        return checklist

    def _build_file_folder_map(
        self, files: list[UploadFile]
    ) -> dict[VdrFolderType, list[UploadFile]]:
        """파일을 VDR 폴더 타입별로 그룹핑한다."""
        result: dict[VdrFolderType, list[UploadFile]] = {}
        for f in files:
            if f.vdr_folder_id:
                folder = self.db.get(VdrFolder, f.vdr_folder_id)
                if folder:
                    result.setdefault(folder.folder_type, []).append(f)
        return result

    def _populate_auto_finding(
        self,
        item: FddChecklistItem,
        category: ChecklistCategory,
        qoe_calc,
        nwc_calc,
        debt_calc,
    ) -> None:
        """엔진 결과를 기반으로 auto_finding, auto_amount를 채운다."""
        # QoE 관련
        if qoe_calc and category in (
            ChecklistCategory.REVENUE_RECOGNITION,
            ChecklistCategory.COGS_CLASSIFICATION,
            ChecklistCategory.SGA_ANALYSIS,
            ChecklistCategory.NON_RECURRING_ITEMS,
            ChecklistCategory.RELATED_PARTY_TRANSACTIONS,
            ChecklistCategory.EBITDA_ADJUSTMENTS,
        ):
            if category == ChecklistCategory.EBITDA_ADJUSTMENTS:
                item.auto_finding = (
                    f"Reported EBITDA: {qoe_calc.reported_ebitda:,.0f}, "
                    f"Adjusted EBITDA: {qoe_calc.adjusted_ebitda:,.0f}, "
                    f"Total Adjustments: {qoe_calc.total_adjustments:,.0f}"
                )
                item.auto_amount = qoe_calc.total_adjustments
            elif category == ChecklistCategory.REVENUE_RECOGNITION:
                breakdown = qoe_calc.category_breakdown or {}
                revenue = breakdown.get("revenue")
                if revenue is not None:
                    item.auto_finding = f"Revenue: {Decimal(str(revenue)):,.0f}"
                    item.auto_amount = Decimal(str(revenue))
            elif category == ChecklistCategory.NON_RECURRING_ITEMS:
                adj_count = len(qoe_calc.adjustment_items or [])
                item.auto_finding = f"{adj_count}건의 조정 후보 항목 자동 식별"
                item.auto_amount = qoe_calc.total_adjustments

        # NWC 관련
        if nwc_calc and category in (
            ChecklistCategory.NWC_CLASSIFICATION,
            ChecklistCategory.AR_AGING,
            ChecklistCategory.AP_AGING,
            ChecklistCategory.INVENTORY_ANALYSIS,
            ChecklistCategory.NWC_SEASONALITY,
        ):
            if category == ChecklistCategory.NWC_CLASSIFICATION:
                item.auto_finding = f"Net Working Capital: {nwc_calc.total_nwc:,.0f}"
                item.auto_amount = nwc_calc.total_nwc

        # Debt 관련
        if debt_calc and category in (
            ChecklistCategory.DEBT_SCHEDULE,
            ChecklistCategory.DEBT_LIKE_ITEMS,
            ChecklistCategory.CASH_LIKE_ITEMS,
            ChecklistCategory.LEASE_OBLIGATIONS,
        ):
            if category == ChecklistCategory.DEBT_SCHEDULE:
                item.auto_finding = (
                    f"Net Debt: {debt_calc.net_debt:,.0f}, "
                    f"Total Debt: {debt_calc.total_debt:,.0f}"
                )
                item.auto_amount = debt_calc.net_debt
            elif category == ChecklistCategory.DEBT_LIKE_ITEMS:
                item.auto_finding = f"Debt-like Items: {debt_calc.debt_like_total:,.0f}"
                item.auto_amount = debt_calc.debt_like_total
            elif category == ChecklistCategory.CASH_LIKE_ITEMS:
                item.auto_finding = f"Cash-like Items: {debt_calc.cash_like_total:,.0f}"
                item.auto_amount = debt_calc.cash_like_total

    def _link_vdr_sources(
        self,
        item: FddChecklistItem,
        category: ChecklistCategory,
        file_folder_map: dict[VdrFolderType, list[UploadFile]],
    ) -> None:
        """체크리스트 항목에 관련 VDR 소스 파일을 연결한다."""
        for folder_type, categories in _FOLDER_TO_CATEGORIES.items():
            if category in categories:
                files = file_folder_map.get(folder_type, [])
                for upload_file in files:
                    link = ChecklistItemVdrLink(
                        checklist_item_id=item.id,
                        upload_file_id=upload_file.id,
                        vdr_folder_id=upload_file.vdr_folder_id,
                        description=f"{upload_file.original_filename} ({folder_type.value})",
                    )
                    self.db.add(link)

    # ── 교차검증 ─────────────────────────────────────────────────────────

    def _run_cross_verification(
        self,
        deal_id: uuid.UUID,
        qoe_calc,
        nwc_calc,
        debt_calc,
        completed_files: list[UploadFile] | None = None,
    ) -> dict[str, Any]:
        """각 엔진 결과에 대해 교차검증을 실행한다.

        Returns:
            {qoe: {...} | None, nwc: {...} | None, debt: {...} | None}
        """
        from app.agents.base import AgentResponse
        from app.agents.cross_verifier import (
            CrossVerificationAgent,
            CrossVerificationResult,
            ReviewMode,
        )
        from app.services.llm.client import create_llm_client
        from app.services.llm.routing.model_router import DEFAULT_FDD_ROUTING

        config = self.cross_verify_config
        review_mode = ReviewMode(config.review_mode)
        results: dict[str, dict[str, Any] | None] = {"qoe": None, "nwc": None, "debt": None}

        # VDR 파싱 데이터에서 GL 항목 추출
        gl_entries = self._extract_gl_entries(completed_files or [])
        deal = self.db.get(Deal, deal_id)
        deal_name = deal.name if deal else str(deal_id)

        for analysis_type, calc, enabled_flag in [
            ("qoe", qoe_calc, config.qoe_enabled),
            ("nwc", nwc_calc, config.nwc_enabled),
            ("debt", debt_calc, config.debt_enabled),
        ]:
            if not enabled_flag or calc is None:
                continue

            try:
                # Writer/Reviewer 프로바이더 결정
                writer_section = {
                    "qoe": "qoe_adjustment_classification",
                    "nwc": "nwc_analysis_narrative",
                    "debt": "debt_analysis_narrative",
                }.get(analysis_type, "qoe_adjustment_classification")

                reviewer_section = f"cross_verify_{analysis_type}"
                writer_provider = DEFAULT_FDD_ROUTING.get(writer_section, "openai")
                reviewer_provider = DEFAULT_FDD_ROUTING.get(reviewer_section, "anthropic")

                reviewer_client = create_llm_client(reviewer_provider)
                if not reviewer_client.is_available():
                    logger.warning(
                        "Reviewer 프로바이더 사용 불가 — %s 교차검증 건너뜀",
                        analysis_type,
                        extra={"ctx": {"provider": reviewer_provider}},
                    )
                    continue

                agent = CrossVerificationAgent(
                    writer_provider=writer_provider,
                    reviewer_provider=reviewer_provider,
                    reviewer_client=reviewer_client,
                    review_mode=review_mode,
                    analysis_type=analysis_type,
                    max_cost_usd=config.max_cost_usd,
                )

                # 엔진 결과를 AgentResponse 형태로 변환
                writer_items = self._calc_to_items(calc, analysis_type)
                writer_result = AgentResponse(
                    success=True,
                    result={"analysis_results": writer_items},
                )
                source_data = {"gl_entries": gl_entries}
                context = {
                    "deal_name": deal_name,
                    "gl_entries": gl_entries,
                    "adjustment_candidates": writer_items,
                }

                cv_result: CrossVerificationResult = agent.run_cross_verification(
                    writer_result, source_data, context,
                )
                results[analysis_type] = asdict(cv_result)

            except Exception as e:
                logger.error(
                    "%s 교차검증 실패: %s", analysis_type, e,
                    extra={"ctx": {"deal_id": str(deal_id)}},
                )

        return results

    def _extract_gl_entries(self, files: list[UploadFile]) -> list[dict[str, Any]]:
        """VDR 파일의 파싱된 메타데이터에서 GL 항목을 추출한다."""
        entries: list[dict[str, Any]] = []
        for f in files:
            parsed = f.parsed_metadata or {}
            # 파싱된 GL 전표가 있으면 추출
            for entry in parsed.get("gl_entries", []):
                entries.append(entry)
            # TB(Trial Balance) 데이터가 있으면 추출
            for account in parsed.get("tb_accounts", []):
                entries.append({
                    "entry_id": account.get("account_code", ""),
                    "account_name": account.get("account_name", ""),
                    "amount": account.get("amount", 0),
                })
        return entries

    def _calc_to_items(self, calc, analysis_type: str) -> list[dict[str, Any]]:
        """엔진 계산 결과를 analysis_results 형태로 변환한다."""
        items: list[dict[str, Any]] = []

        if analysis_type == "qoe" and hasattr(calc, "adjustment_items"):
            for adj in (calc.adjustment_items or []):
                items.append({
                    "entry_id": str(getattr(adj, "id", "")),
                    "assessment": getattr(adj, "category", "OPERATING"),
                    "amount": str(getattr(adj, "amount", 0)),
                    "rationale": getattr(adj, "description", ""),
                    "confidence": getattr(adj, "confidence", 0.8),
                })

        elif analysis_type == "nwc" and hasattr(calc, "line_items"):
            for li in (calc.line_items or []):
                items.append({
                    "entry_id": str(getattr(li, "account_code", getattr(li, "id", ""))),
                    "classification": getattr(li, "classification", "").name
                    if hasattr(getattr(li, "classification", None), "name")
                    else str(getattr(li, "classification", "")),
                    "amount": str(getattr(li, "amount", 0)),
                    "rationale": getattr(li, "account_name", ""),
                    "confidence": 0.8,
                })

        elif analysis_type == "debt" and hasattr(calc, "items"):
            for di in (calc.items or []):
                items.append({
                    "entry_id": str(getattr(di, "source_account_code", getattr(di, "id", ""))),
                    "item_type": getattr(di, "item_type", "").name
                    if hasattr(getattr(di, "item_type", None), "name")
                    else str(getattr(di, "item_type", "")),
                    "debt_like": getattr(di, "item_type", "").name in ("DEBT_LIKE",)
                    if hasattr(getattr(di, "item_type", None), "name")
                    else False,
                    "amount": str(getattr(di, "amount", 0)),
                    "rationale": getattr(di, "description", ""),
                    "confidence": float(getattr(di, "confidence_score", 80)) / 100
                    if getattr(di, "confidence_score", None) is not None
                    else 0.8,
                })

        return items

    def _apply_cv_flags(
        self,
        checklist: FddChecklist,
        cv_results: dict[str, Any],
    ) -> None:
        """교차검증 결과를 체크리스트 항목에 반영한다.

        - 불일치 항목 → FLAGGED + notes에 양측 근거
        - Reviewer만 발견한 항목 → 새 FddChecklistItem 추가 (FLAGGED)
        - 자동 해결 항목 → extra_metadata에 해결 근거
        """
        # 분석 유형별 관련 카테고리 매핑
        type_to_categories: dict[str, list[ChecklistCategory]] = {
            "qoe": [
                ChecklistCategory.REVENUE_RECOGNITION,
                ChecklistCategory.NON_RECURRING_ITEMS,
                ChecklistCategory.EBITDA_ADJUSTMENTS,
            ],
            "nwc": [
                ChecklistCategory.NWC_CLASSIFICATION,
                ChecklistCategory.AR_AGING,
            ],
            "debt": [
                ChecklistCategory.DEBT_SCHEDULE,
                ChecklistCategory.DEBT_LIKE_ITEMS,
            ],
        }

        for analysis_type, cv_data in cv_results.items():
            if cv_data is None:
                continue

            disagreements = cv_data.get("disagreements", [])
            reviewer_only = cv_data.get("reviewer_only_items", [])
            categories = type_to_categories.get(analysis_type, [])

            if not categories or (not disagreements and not reviewer_only):
                continue

            # 모든 관련 카테고리 항목에 FLAGGED 마킹
            flag_notes = []
            for d in disagreements:
                resolved_text = f" [자동해결: {d.get('resolution', '')}]" if d.get("resolved") else ""
                flag_notes.append(
                    f"[{d.get('level', 'UNKNOWN')}] {d.get('field', '')}: "
                    f"Writer={d.get('writer_value', '')} vs Reviewer={d.get('reviewer_value', '')}"
                    f"{resolved_text}"
                )

            cv_meta = {
                "cross_verification": {
                    "analysis_type": analysis_type,
                    "writer_provider": cv_data.get("writer_provider"),
                    "reviewer_provider": cv_data.get("reviewer_provider"),
                    "agreement_rate": cv_data.get("agreement_rate"),
                    "disagreements": disagreements,
                }
            }

            for item in checklist.items:
                if item.category in categories and disagreements:
                    item.status = ChecklistItemStatus.FLAGGED

                    existing_desc = item.description or ""
                    item.description = (
                        f"{existing_desc}\n\n"
                        f"── 교차검증 불일치 ({len(disagreements)}건) ──\n"
                        + "\n".join(flag_notes)
                    )
                    item.extra_metadata = cv_meta

            # Reviewer만 발견한 항목 → 새 FddChecklistItem 추가 (FLAGGED)
            if reviewer_only and categories:
                target_category = categories[0]
                max_order = max((it.order_index for it in checklist.items), default=0)
                for idx, ro_item in enumerate(reviewer_only):
                    new_item = FddChecklistItem(
                        checklist_id=checklist.id,
                        category=target_category,
                        order_index=max_order + 1 + idx,
                        title=f"[Reviewer 발견] {ro_item.get('entry_id', 'Unknown')}",
                        description=(
                            f"Reviewer만 식별한 항목 — {ro_item.get('rationale', '')}\n"
                            f"Assessment: {ro_item.get('assessment', ro_item.get('classification', 'N/A'))}, "
                            f"Amount: {ro_item.get('amount', 'N/A')}"
                        ),
                        severity=ChecklistSeverity.HIGH,
                        status=ChecklistItemStatus.FLAGGED,
                        extra_metadata={
                            "cross_verification": {
                                "source": "reviewer_only",
                                "analysis_type": analysis_type,
                                "reviewer_provider": cv_data.get("reviewer_provider"),
                                "original_item": ro_item,
                            }
                        },
                    )
                    self.db.add(new_item)
