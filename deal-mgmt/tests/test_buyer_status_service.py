"""buyer_status_service 단위 테스트 — 마케팅 스테이지 기반 자동 승격 로직."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import BuyerCandidateStatus, MarketingStage
from app.services.buyer_status_service import (
    ADVANCE_PATH,
    MARKETING_STATUS_ADVANCE,
    STATUS_ORDER,
    TERMINAL_STATUSES,
    auto_advance_buyer_status,
    check_status_after_delete,
    get_advance_target,
    has_advance_mapping,
)

_S = BuyerCandidateStatus


# ── 순수 함수 테스트 ──────────────────────────────────────


class TestGetAdvanceTarget:
    """get_advance_target: 마케팅 스테이지 → 목표 buyer status 매핑."""

    def test_teaser_sent_maps_to_contacted(self) -> None:
        assert get_advance_target(MarketingStage.TEASER_SENT) == _S.CONTACTED

    def test_im_distributed_maps_to_cim_sent(self) -> None:
        assert get_advance_target(MarketingStage.IM_DISTRIBUTED) == _S.CIM_SENT

    def test_loi_received_maps_to_loi_received(self) -> None:
        assert get_advance_target(MarketingStage.LOI_RECEIVED) == _S.LOI_RECEIVED

    def test_nda_signed_maps_to_nda_signed(self) -> None:
        assert get_advance_target(MarketingStage.NDA_SIGNED) == _S.NDA_SIGNED

    def test_dd_in_progress_maps_to_dd_in_progress(self) -> None:
        assert get_advance_target(MarketingStage.DD_IN_PROGRESS) == _S.DD_IN_PROGRESS

    def test_identified_has_no_mapping(self) -> None:
        assert get_advance_target(MarketingStage.IDENTIFIED) is None

    def test_mgmt_presentation_has_no_mapping(self) -> None:
        assert get_advance_target(MarketingStage.MGMT_PRESENTATION) is None


class TestHasAdvanceMapping:
    """has_advance_mapping: 매핑 존재 여부."""

    def test_teaser_sent_has_mapping(self) -> None:
        assert has_advance_mapping(MarketingStage.TEASER_SENT) is True

    def test_identified_has_no_mapping(self) -> None:
        assert has_advance_mapping(MarketingStage.IDENTIFIED) is False

    def test_mgmt_presentation_has_no_mapping(self) -> None:
        assert has_advance_mapping(MarketingStage.MGMT_PRESENTATION) is False


class TestDataStructureIntegrity:
    """데이터 구조 무결성 확인."""

    def test_all_advance_targets_in_status_order(self) -> None:
        """MARKETING_STATUS_ADVANCE의 모든 목표 상태가 STATUS_ORDER에 존재해야 한다."""
        for target in MARKETING_STATUS_ADVANCE.values():
            assert target in STATUS_ORDER, f"{target} not in STATUS_ORDER"

    def test_all_advance_path_keys_in_status_order(self) -> None:
        """ADVANCE_PATH의 모든 키가 STATUS_ORDER에 존재해야 한다."""
        for key in ADVANCE_PATH:
            assert key in STATUS_ORDER, f"{key} not in STATUS_ORDER"

    def test_all_advance_path_values_in_status_order(self) -> None:
        """ADVANCE_PATH의 모든 값이 STATUS_ORDER에 존재해야 한다."""
        for value in ADVANCE_PATH.values():
            assert value in STATUS_ORDER, f"{value} not in STATUS_ORDER"

    def test_advance_path_always_goes_forward(self) -> None:
        """ADVANCE_PATH의 각 전이는 항상 더 높은 ordinal로 이동해야 한다."""
        for src, dst in ADVANCE_PATH.items():
            assert STATUS_ORDER[src] < STATUS_ORDER[dst], (
                f"{src} (ord={STATUS_ORDER[src]}) -> {dst} (ord={STATUS_ORDER[dst]}) goes backward"
            )

    def test_terminal_statuses_not_in_advance_path(self) -> None:
        """터미널 상태는 ADVANCE_PATH 키에 존재하면 안 된다."""
        for status in TERMINAL_STATUSES:
            assert status not in ADVANCE_PATH, f"Terminal status {status} should not be in ADVANCE_PATH"


# ── auto_advance_buyer_status 비동기 테스트 ──────────────


def _make_buyer(status: BuyerCandidateStatus) -> MagicMock:
    """테스트용 BuyerCandidate mock 생성."""
    buyer = MagicMock()
    buyer.id = uuid.uuid4()
    buyer.status = status
    return buyer


@pytest.mark.asyncio
class TestAutoAdvanceBuyerStatus:
    """auto_advance_buyer_status: 멀티홉 상태 승격."""

    @patch("app.services.buyer_status_service.audit_service")
    async def test_identified_to_contacted(self, mock_audit: MagicMock) -> None:
        """IDENTIFIED → CONTACTED (1홉)."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        buyer = _make_buyer(_S.IDENTIFIED)

        await auto_advance_buyer_status(db, buyer, _S.CONTACTED, "test@test.com")

        assert buyer.status == _S.CONTACTED
        mock_audit.record.assert_called_once()

    @patch("app.services.buyer_status_service.audit_service")
    async def test_identified_to_nda_signed_multi_hop(self, mock_audit: MagicMock) -> None:
        """IDENTIFIED → CONTACTED → NDA_SIGNED (2홉)."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        buyer = _make_buyer(_S.IDENTIFIED)

        await auto_advance_buyer_status(db, buyer, _S.NDA_SIGNED, "test@test.com")

        assert buyer.status == _S.NDA_SIGNED
        assert mock_audit.record.call_count == 2

    @patch("app.services.buyer_status_service.audit_service")
    async def test_nda_sent_to_nda_signed(self, mock_audit: MagicMock) -> None:
        """NDA_SENT → NDA_SIGNED (NDA_SENT가 있는 buyer도 정상 처리)."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        buyer = _make_buyer(_S.NDA_SENT)

        await auto_advance_buyer_status(db, buyer, _S.NDA_SIGNED, "test@test.com")

        assert buyer.status == _S.NDA_SIGNED
        mock_audit.record.assert_called_once()

    @patch("app.services.buyer_status_service.audit_service")
    async def test_already_at_target_no_change(self, mock_audit: MagicMock) -> None:
        """이미 목표 상태이면 변경 없음 (멱등성)."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        buyer = _make_buyer(_S.NDA_SIGNED)

        await auto_advance_buyer_status(db, buyer, _S.NDA_SIGNED, "test@test.com")

        assert buyer.status == _S.NDA_SIGNED
        mock_audit.record.assert_not_called()

    @patch("app.services.buyer_status_service.audit_service")
    async def test_above_target_no_change(self, mock_audit: MagicMock) -> None:
        """목표보다 높은 상태이면 변경 없음."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        buyer = _make_buyer(_S.DD_IN_PROGRESS)

        await auto_advance_buyer_status(db, buyer, _S.CONTACTED, "test@test.com")

        assert buyer.status == _S.DD_IN_PROGRESS
        mock_audit.record.assert_not_called()

    @patch("app.services.buyer_status_service.audit_service")
    async def test_terminal_status_rejected_no_change(self, mock_audit: MagicMock) -> None:
        """터미널 상태(REJECTED)는 승격하지 않음."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        buyer = _make_buyer(_S.REJECTED)

        await auto_advance_buyer_status(db, buyer, _S.NDA_SIGNED, "test@test.com")

        assert buyer.status == _S.REJECTED
        mock_audit.record.assert_not_called()

    @patch("app.services.buyer_status_service.audit_service")
    async def test_terminal_status_bid_dropped_no_change(self, mock_audit: MagicMock) -> None:
        """터미널 상태(BID_DROPPED)는 승격하지 않음."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        buyer = _make_buyer(_S.BID_DROPPED)

        await auto_advance_buyer_status(db, buyer, _S.CIM_SENT, "test@test.com")

        assert buyer.status == _S.BID_DROPPED
        mock_audit.record.assert_not_called()

    @patch("app.services.buyer_status_service.audit_service")
    async def test_status_not_in_order_no_change(self, mock_audit: MagicMock) -> None:
        """STATUS_ORDER에 없는 상태(BID_SUBMITTED 등)는 변경 없음."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        # BID_SUBMITTED는 STATUS_ORDER에 있으므로, 임의로 터미널 상태 확인
        buyer = _make_buyer(_S.BID_NOT_SUBMITTED)

        await auto_advance_buyer_status(db, buyer, _S.CONTACTED, "test@test.com")

        assert buyer.status == _S.BID_NOT_SUBMITTED
        mock_audit.record.assert_not_called()

    @patch("app.services.buyer_status_service.audit_service")
    async def test_audit_records_old_and_new_values(self, mock_audit: MagicMock) -> None:
        """감사 로그에 old_value와 new_value가 올바르게 기록되는지 확인."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        buyer = _make_buyer(_S.IDENTIFIED)

        await auto_advance_buyer_status(db, buyer, _S.CONTACTED, "actor@test.com")

        call_kwargs = mock_audit.record.call_args.kwargs
        assert call_kwargs["old_value"] == {"status": "IDENTIFIED"}
        assert call_kwargs["new_value"] == {"status": "CONTACTED"}
        assert call_kwargs["actor_email"] == "actor@test.com"
        assert call_kwargs["notes"] == "마케팅 스테이지 기반 자동 승격"


@pytest.mark.asyncio
class TestCheckStatusAfterDelete:
    """check_status_after_delete: 삭제 시 감사 경고 로그."""

    @patch("app.services.buyer_status_service.audit_service")
    async def test_mapped_stage_logs_warning(self, mock_audit: MagicMock) -> None:
        """자동 승격 매핑이 있는 스테이지 삭제 시 감사 로그 기록."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        buyer_id = uuid.uuid4()

        await check_status_after_delete(db, buyer_id, MarketingStage.NDA_SIGNED, "actor@test.com")

        mock_audit.record.assert_called_once()
        call_kwargs = mock_audit.record.call_args.kwargs
        assert "마케팅 로그 삭제됨" in call_kwargs["notes"]
        assert "NDA_SIGNED" in call_kwargs["notes"]
        assert "수동 검토 필요" in call_kwargs["notes"]

    @patch("app.services.buyer_status_service.audit_service")
    async def test_unmapped_stage_no_log(self, mock_audit: MagicMock) -> None:
        """자동 승격 매핑이 없는 스테이지 삭제 시 감사 로그 미기록."""
        mock_audit.record = AsyncMock()
        db = AsyncMock()
        buyer_id = uuid.uuid4()

        await check_status_after_delete(db, buyer_id, MarketingStage.IDENTIFIED, "actor@test.com")

        mock_audit.record.assert_not_called()
