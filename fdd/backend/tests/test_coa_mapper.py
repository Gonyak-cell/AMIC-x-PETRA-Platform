"""CoA 매핑 엔진 단위 테스트 — FDD-302."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account_mapping import AccountMapping, MappingConfidence, MappingStatus
from app.models.standard_line_item import (
    FinancialStatement,
    LineItemCategory,
    StandardLineItem,
)
from app.schemas.mapping import AccountMappingCreate
from app.services.mapping.coa_mapper import (
    _exact_match,
    _fuzzy_match,
    _keyword_match,
    _score_to_confidence,
    approve_mapping,
    save_mappings,
    suggest_mappings,
)

# ── Fixtures ──────────────────────────────────────────────


def _make_line_items(db: Session) -> list[StandardLineItem]:
    """테스트용 표준 라인아이템 10개 생성."""
    items_data = [
        (
            "IS-REV-001",
            "Revenue",
            "매출액",
            "REVENUE",
            "IS",
            100,
            ["매출", "수익", "revenue", "sales"],
        ),
        (
            "IS-COGS-001",
            "Cost of Goods Sold",
            "매출원가",
            "COGS",
            "IS",
            200,
            ["매출원가", "원가", "COGS"],
        ),
        (
            "IS-SGA-001",
            "SG&A",
            "판매비와관리비",
            "SGA",
            "IS",
            300,
            ["판관비", "판매비", "SGA"],
        ),
        (
            "IS-SGA-002",
            "Salaries & Wages",
            "급여",
            "SGA",
            "IS",
            310,
            ["급여", "임금", "salaries"],
        ),
        (
            "BS-CASH-001",
            "Cash",
            "현금및현금성자산",
            "CASH",
            "BS",
            1000,
            ["현금", "cash"],
        ),
        (
            "BS-AR-001",
            "Accounts Receivable",
            "매출채권",
            "AR",
            "BS",
            1100,
            ["매출채권", "외상매출금", "receivable"],
        ),
        (
            "BS-INV-001",
            "Inventory",
            "재고자산",
            "INVENTORY",
            "BS",
            1200,
            ["재고", "inventory"],
        ),
        (
            "BS-AP-001",
            "Accounts Payable",
            "매입채무",
            "AP",
            "BS",
            2000,
            ["매입채무", "payable"],
        ),
        (
            "BS-DEBT-001",
            "Short-term Borrowings",
            "단기차입금",
            "DEBT",
            "BS",
            2300,
            ["단기차입금", "borrowings"],
        ),
        (
            "BS-EQ-001",
            "Share Capital",
            "자본금",
            "EQUITY",
            "BS",
            3000,
            ["자본금", "share capital"],
        ),
    ]

    items: list[StandardLineItem] = []
    for code, en, ko, cat, stmt, order, kw in items_data:
        item = StandardLineItem(
            code=code,
            name_en=en,
            name_ko=ko,
            category=LineItemCategory(cat),
            statement_type=FinancialStatement(stmt),
            display_order=order,
            is_subtotal=False,
            keywords=kw,
        )
        db.add(item)
        items.append(item)

    db.commit()
    return items


def _make_deal(db: Session) -> uuid.UUID:
    """테스트용 Deal 생성."""
    from app.models.deal import Deal, DealType

    deal = Deal(
        name="Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    db.add(deal)
    db.flush()
    return deal.id


# ── _exact_match ──────────────────────────────────────────


class TestExactMatch:
    def test_exact_ko_match(self, db: Session):
        items = _make_line_items(db)
        result = _exact_match("매출액", items)
        assert result is not None
        assert result[0].code == "IS-REV-001"
        assert result[1] == Decimal("100.00")

    def test_exact_en_match(self, db: Session):
        items = _make_line_items(db)
        result = _exact_match("Revenue", items)
        assert result is not None
        assert result[0].code == "IS-REV-001"

    def test_exact_case_insensitive(self, db: Session):
        items = _make_line_items(db)
        result = _exact_match("revenue", items)
        assert result is not None
        assert result[0].code == "IS-REV-001"

    def test_exact_whitespace_handling(self, db: Session):
        items = _make_line_items(db)
        result = _exact_match("  매출액  ", items)
        assert result is not None
        assert result[0].code == "IS-REV-001"

    def test_exact_no_match(self, db: Session):
        items = _make_line_items(db)
        result = _exact_match("알수없는계정", items)
        assert result is None


# ── _keyword_match ────────────────────────────────────────


class TestKeywordMatch:
    def test_keyword_match_ko(self, db: Session):
        items = _make_line_items(db)
        result = _keyword_match("매출관련비용", items)
        # "매출" 키워드는 IS-REV-001 (매출, 수익...)에 매칭
        assert result is not None
        assert result[1] == Decimal("75.00")

    def test_keyword_match_en(self, db: Session):
        items = _make_line_items(db)
        result = _keyword_match("Total Sales Amount", items)
        assert result is not None
        # "sales" 키워드 매칭
        assert result[0].code == "IS-REV-001"

    def test_keyword_longest_match(self, db: Session):
        items = _make_line_items(db)
        # "매출원가" 키워드 (4글자) > "매출" (2글자)
        result = _keyword_match("매출원가계정", items)
        assert result is not None
        assert result[0].code == "IS-COGS-001"

    def test_keyword_no_match(self, db: Session):
        items = _make_line_items(db)
        result = _keyword_match("XYZ특수계정", items)
        assert result is None


# ── _fuzzy_match ──────────────────────────────────────────


class TestFuzzyMatch:
    def test_fuzzy_similar_name(self, db: Session):
        items = _make_line_items(db)
        result = _fuzzy_match("현금및예금", items)
        assert result is not None
        # "현금및현금성자산"과 유사
        assert result[0].code == "BS-CASH-001"

    def test_fuzzy_above_threshold(self, db: Session):
        items = _make_line_items(db)
        result = _fuzzy_match("Accounts Receivabl", items)
        assert result is not None
        assert result[0].code == "BS-AR-001"
        assert result[1] >= Decimal("50.0")

    def test_fuzzy_below_threshold(self, db: Session):
        items = _make_line_items(db)
        result = _fuzzy_match("ZZZZ", items)
        assert result is None

    def test_fuzzy_custom_threshold(self, db: Session):
        items = _make_line_items(db)
        result = _fuzzy_match("현금", items, threshold=Decimal("80.0"))
        # 유사도가 80% 미만이면 None
        # "현금" vs "현금및현금성자산" 유사도가 낮을 수 있음
        # 결과는 threshold에 따라 다를 수 있음
        if result is not None:
            assert result[1] >= Decimal("80.0")


# ── _score_to_confidence ──────────────────────────────────


class TestScoreToConfidence:
    def test_high_confidence(self):
        assert _score_to_confidence(Decimal("95")) == MappingConfidence.HIGH
        assert _score_to_confidence(Decimal("90")) == MappingConfidence.HIGH

    def test_medium_confidence(self):
        assert _score_to_confidence(Decimal("75")) == MappingConfidence.MEDIUM
        assert _score_to_confidence(Decimal("70")) == MappingConfidence.MEDIUM

    def test_low_confidence(self):
        assert _score_to_confidence(Decimal("50")) == MappingConfidence.LOW
        assert _score_to_confidence(Decimal("69")) == MappingConfidence.LOW


# ── suggest_mappings ──────────────────────────────────────


class TestSuggestMappings:
    def test_exact_match_result(self, db: Session):
        items = _make_line_items(db)
        tb_accounts = [("1001", "매출액", Decimal("1000000"))]
        suggestions = suggest_mappings(items, tb_accounts)

        assert len(suggestions) == 1
        s = suggestions[0]
        assert s.suggested_target_code == "IS-REV-001"
        assert s.confidence == MappingConfidence.HIGH
        assert s.algorithm == "exact"
        assert s.match_score == Decimal("100.00")

    def test_keyword_match_result(self, db: Session):
        items = _make_line_items(db)
        tb_accounts = [("2001", "급여비용", Decimal("500000"))]
        suggestions = suggest_mappings(items, tb_accounts)

        assert len(suggestions) == 1
        s = suggestions[0]
        assert s.confidence == MappingConfidence.MEDIUM
        assert s.algorithm == "keyword"

    def test_unmapped_result(self, db: Session):
        items = _make_line_items(db)
        tb_accounts = [("9999", "XYZABC특수계정", Decimal("100"))]
        suggestions = suggest_mappings(items, tb_accounts)

        assert len(suggestions) == 1
        s = suggestions[0]
        assert s.confidence == MappingConfidence.UNMAPPED
        assert s.suggested_target_code == ""
        assert s.algorithm == "none"

    def test_multiple_accounts(self, db: Session):
        items = _make_line_items(db)
        tb_accounts = [
            ("1001", "매출액", Decimal("5000000")),
            ("2001", "매출원가", Decimal("3000000")),
            ("3001", "급여", Decimal("1000000")),
            ("9999", "XYZABC", Decimal("100")),
        ]
        suggestions = suggest_mappings(items, tb_accounts)
        assert len(suggestions) == 4

        # 매출액 → exact
        assert suggestions[0].algorithm == "exact"
        # 매출원가 → exact
        assert suggestions[1].algorithm == "exact"
        # 급여 → exact
        assert suggestions[2].algorithm == "exact"
        # XYZABC → unmapped
        assert suggestions[3].confidence == MappingConfidence.UNMAPPED

    def test_empty_tb_accounts(self, db: Session):
        items = _make_line_items(db)
        suggestions = suggest_mappings(items, [])
        assert len(suggestions) == 0

    def test_affected_amount_preserved(self, db: Session):
        items = _make_line_items(db)
        tb_accounts = [("1001", "매출액", Decimal("12345678.1234"))]
        suggestions = suggest_mappings(items, tb_accounts)
        assert suggestions[0].affected_amount == Decimal("12345678.1234")


# ── save_mappings ─────────────────────────────────────────


class TestSaveMappings:
    def test_save_creates_records(self, db: Session):
        _make_line_items(db)
        deal_id = _make_deal(db)

        mappings_data = [
            AccountMappingCreate(
                source_account_code="1001",
                source_account_name="매출액",
                target_line_item_code="IS-REV-001",
                confidence=MappingConfidence.HIGH,
                match_score=Decimal("100.00"),
                algorithm="exact",
                affected_amount=Decimal("5000000"),
            ),
        ]
        saved = save_mappings(db, deal_id, mappings_data)

        assert len(saved) == 1
        assert saved[0].deal_id == deal_id
        assert saved[0].source_account_code == "1001"
        assert saved[0].status == MappingStatus.PROPOSED

    def test_save_creates_audit_log(self, db: Session):
        from app.models.audit import AuditLog

        _make_line_items(db)
        deal_id = _make_deal(db)

        mappings_data = [
            AccountMappingCreate(
                source_account_code="2001",
                source_account_name="매출원가",
                target_line_item_code="IS-COGS-001",
                confidence=MappingConfidence.HIGH,
                match_score=Decimal("100.00"),
                algorithm="exact",
                affected_amount=Decimal("3000000"),
            ),
        ]
        save_mappings(db, deal_id, mappings_data)

        from sqlalchemy import select

        logs = list(
            db.scalars(
                select(AuditLog).where(AuditLog.entity_type == "account_mapping")
            )
        )
        assert len(logs) >= 1
        assert logs[0].action.value == "CREATE"

    def test_save_multiple_mappings(self, db: Session):
        _make_line_items(db)
        deal_id = _make_deal(db)

        mappings_data = [
            AccountMappingCreate(
                source_account_code=f"A{i}",
                source_account_name=f"Account {i}",
                target_line_item_code="IS-REV-001",
                confidence=MappingConfidence.MEDIUM,
                affected_amount=Decimal("1000"),
            )
            for i in range(5)
        ]
        saved = save_mappings(db, deal_id, mappings_data)
        assert len(saved) == 5


# ── approve_mapping ───────────────────────────────────────


class TestApproveMapping:
    def test_approve_changes_status(self, db: Session):
        _make_line_items(db)
        deal_id = _make_deal(db)

        mapping = AccountMapping(
            deal_id=deal_id,
            source_account_code="1001",
            source_account_name="매출액",
            target_line_item_code="IS-REV-001",
            confidence=MappingConfidence.HIGH,
            status=MappingStatus.PROPOSED,
            affected_amount=Decimal("5000000"),
        )
        db.add(mapping)
        db.flush()

        approved = approve_mapping(db, mapping, "tester")
        assert approved.status == MappingStatus.APPROVED
        assert approved.approved_by == "tester"
        assert approved.approved_at is not None

    def test_approve_creates_audit_log(self, db: Session):
        from sqlalchemy import select

        from app.models.audit import AuditLog

        _make_line_items(db)
        deal_id = _make_deal(db)

        mapping = AccountMapping(
            deal_id=deal_id,
            source_account_code="2001",
            source_account_name="매출원가",
            target_line_item_code="IS-COGS-001",
            confidence=MappingConfidence.HIGH,
            status=MappingStatus.PROPOSED,
            affected_amount=Decimal("3000000"),
        )
        db.add(mapping)
        db.flush()

        approve_mapping(db, mapping, "admin")

        logs = list(
            db.scalars(
                select(AuditLog).where(
                    AuditLog.entity_type == "account_mapping",
                    AuditLog.action == "APPROVE",
                )
            )
        )
        assert len(logs) >= 1
