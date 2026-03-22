from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attachment import Attachment
from app.models.bid import Bid
from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import BidType, ValuationMethod
from app.ralph.parsers import parse_file

_BID_TYPE_RULES: tuple[tuple[BidType, tuple[str, ...]], ...] = (
    (
        BidType.FINAL_OFFER,
        (
            r"\bfinal offer\b",
            r"\bbest and final\b",
            r"\bbinding offer\b",
            "최종 제안",
            "최종입찰",
            "본입찰",
        ),
    ),
    (
        BidType.LOI,
        (
            r"\bloi\b",
            "letter of intent",
            "인수의향서",
            "투자의향서",
        ),
    ),
    (
        BidType.IOI,
        (
            r"\bioi\b",
            "indication of interest",
            "non-binding offer",
            "예비입찰",
            "인수의향",
            "관심표명",
        ),
    ),
)

_AMOUNT_HINTS = (
    "offer",
    "purchase price",
    "bid amount",
    "equity value",
    "enterprise value",
    "consideration",
    "valuation",
    "제안가",
    "입찰가",
    "인수가",
    "인수금액",
    "매매대금",
    "거래가치",
)

_VALID_UNTIL_HINTS = (
    "valid until",
    "valid through",
    "expiry",
    "expiration",
    "expires",
    "유효기간",
    "유효",
    "만료",
)

_SUBMITTED_AT_HINTS = (
    "submitted",
    "dated",
    "date",
    "제출일",
    "제안일",
    "일자",
)

_DATE_RE = re.compile(r"(?<!\d)(20\d{2})[./-](\d{1,2})[./-](\d{1,2})(?!\d)")
_KRW_UNIT_RE = re.compile(
    r"(?P<num>\d{1,4}(?:,\d{3})*(?:\.\d+)?)\s*(?P<unit>조원|억원|억|조|만원|만|원)"
)
_FX_AMOUNT_RE = re.compile(
    r"(?P<prefix>KRW|USD|US\$|EUR|\$|€)?\s*(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{8,})(?:\s*(?P<suffix>KRW|USD|US\$|EUR|\$|€|원))?",
    re.IGNORECASE,
)
_MULTIPLE_PATTERNS = (
    re.compile(
        r"(?P<multiple>\d{1,2}(?:\.\d+)?)\s*x\s*(?P<context>ebitda|ev\s*/\s*ebitda|revenue|sales|book)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<context>ev\s*/\s*ebitda|ebitda|ev\s*/\s*revenue|ev\s*/\s*sales|revenue|sales|book)"
        r"\s*(?:multiple\s*)?(?P<multiple>\d{1,2}(?:\.\d+)?)\s*x",
        re.IGNORECASE,
    ),
)


@dataclass
class BidImportAnalysis:
    buyer: BuyerCandidate
    bid_type: BidType
    amount: Decimal | None = None
    currency: str = "KRW"
    submitted_at: str | None = None
    valid_until: str | None = None
    valuation_method: ValuationMethod | None = None
    multiple: Decimal | None = None
    inferred_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    return re.sub(r"\s+", " ", normalized).strip()


def _normalize_compact(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    return re.sub(r"[^0-9a-z가-힣]+", "", normalized)


def _to_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return None


def _format_iso_date(year: str, month: str, day: str) -> str:
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _extract_date_near_keywords(text: str, keywords: tuple[str, ...]) -> str | None:
    lowered = _normalize_text(text)
    for keyword in keywords:
        index = lowered.find(keyword)
        if index < 0:
            continue
        window = lowered[index : index + 120]
        match = _DATE_RE.search(window)
        if match:
            return _format_iso_date(*match.groups())
    return None


def _extract_first_date(text: str) -> str | None:
    match = _DATE_RE.search(unicodedata.normalize("NFKC", text or ""))
    if not match:
        return None
    return _format_iso_date(*match.groups())


def _extract_bid_type(text: str) -> BidType | None:
    source = _normalize_text(text)
    for bid_type, rules in _BID_TYPE_RULES:
        if any(re.search(rule, source) for rule in rules):
            return bid_type
    return None


def _extract_valuation_method(text: str) -> ValuationMethod | None:
    source = _normalize_text(text)
    if re.search(r"ev\s*/\s*ebitda|ebitda multiple|ebitda", source):
        return ValuationMethod.EV_EBITDA
    if re.search(r"ev\s*/\s*revenue|ev\s*/\s*sales|revenue multiple|sales multiple|매출", source):
        return ValuationMethod.EV_REVENUE
    if re.search(r"price\s*/\s*book|p\s*/\s*b|book value|순자산", source):
        return ValuationMethod.PRICE_BOOK
    if "dcf" in source or "discounted cash flow" in source:
        return ValuationMethod.DCF
    if "comparable" in source or "peer multiple" in source or "comps" in source:
        return ValuationMethod.COMPARABLE
    return None


def _extract_multiple(text: str) -> Decimal | None:
    source = _normalize_text(text)
    for pattern in _MULTIPLE_PATTERNS:
        match = pattern.search(source)
        if match:
            return _to_decimal(match.group("multiple"))
    return None


def _candidate_currency(prefix: str | None, suffix: str | None) -> str:
    token = (prefix or suffix or "").upper()
    if token in {"USD", "US$", "$"}:
        return "USD"
    if token in {"EUR", "€"}:
        return "EUR"
    return "KRW"


def _extract_amount_candidates(text: str) -> list[tuple[Decimal, str]]:
    source = unicodedata.normalize("NFKC", text or "")
    candidates: list[tuple[Decimal, str]] = []

    for match in _KRW_UNIT_RE.finditer(source):
        number = _to_decimal(match.group("num"))
        if number is None:
            continue
        unit = match.group("unit")
        multiplier = Decimal("1")
        if unit in {"조", "조원"}:
            multiplier = Decimal("1000000000000")
        elif unit in {"억", "억원"}:
            multiplier = Decimal("100000000")
        elif unit in {"만", "만원"}:
            multiplier = Decimal("10000")
        amount = number * multiplier
        if amount >= Decimal("1000000"):
            candidates.append((amount, "KRW"))

    for match in _FX_AMOUNT_RE.finditer(source):
        number = _to_decimal(match.group("num"))
        if number is None or number < Decimal("1000000"):
            continue
        currency = _candidate_currency(match.group("prefix"), match.group("suffix"))
        candidates.append((number, currency))

    deduped: list[tuple[Decimal, str]] = []
    seen: set[tuple[str, str]] = set()
    for amount, currency in candidates:
        key = (str(amount), currency)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((amount, currency))
    return deduped


def _extract_amount(text: str) -> tuple[Decimal | None, str]:
    lines = [line.strip() for line in unicodedata.normalize("NFKC", text or "").splitlines() if line.strip()]
    prioritized_lines = [
        line
        for line in lines
        if any(hint in line.lower() for hint in _AMOUNT_HINTS)
    ]

    for bucket in (prioritized_lines, lines):
        if not bucket:
            continue
        candidates: list[tuple[Decimal, str]] = []
        for line in bucket:
            candidates.extend(_extract_amount_candidates(line))
        if candidates:
            amount, currency = max(candidates, key=lambda item: item[0])
            return amount, currency

    fallback_candidates = _extract_amount_candidates(text)
    if not fallback_candidates:
        return None, "KRW"
    amount, currency = max(fallback_candidates, key=lambda item: item[0])
    return amount, currency


async def _load_buyers(db: AsyncSession, txn_id: uuid.UUID) -> list[BuyerCandidate]:
    result = await db.execute(
        select(BuyerCandidate)
        .where(BuyerCandidate.transaction_id == txn_id)
        .order_by(BuyerCandidate.created_at.desc())
    )
    return list(result.scalars().all())


def _match_buyer_from_text(buyers: list[BuyerCandidate], source_text: str) -> BuyerCandidate | None:
    haystack_compact = _normalize_compact(source_text)
    haystack_spaced = _normalize_text(source_text)

    best_match: BuyerCandidate | None = None
    best_score = 0
    for buyer in buyers:
        compact_name = _normalize_compact(buyer.company_name)
        if len(compact_name) >= 2 and compact_name in haystack_compact:
            score = len(compact_name) * 10
        else:
            score = 0
            for token in _normalize_text(buyer.company_name).split():
                if len(token) < 2:
                    continue
                if token in haystack_spaced:
                    score += len(token)
        if score > best_score:
            best_score = score
            best_match = buyer
    return best_match if best_score > 0 else None


async def analyze_bid_attachment(
    db: AsyncSession,
    txn_id: uuid.UUID,
    attachment: Attachment,
    *,
    buyer_candidate_id: uuid.UUID | None = None,
    bid_type: BidType | None = None,
) -> BidImportAnalysis:
    parsed = parse_file(attachment.file_path)
    source_text = "\n".join(
        part for part in [attachment.file_name, parsed.text or ""] if part
    )

    buyers = await _load_buyers(db, txn_id)
    buyer: BuyerCandidate | None = None
    warnings: list[str] = []

    if buyer_candidate_id is not None:
        buyer = next((item for item in buyers if item.id == buyer_candidate_id), None)
        if buyer is None:
            raise ValueError("선택한 매수후보를 찾을 수 없습니다.")
    else:
        buyer = _match_buyer_from_text(buyers, source_text)
        if buyer is None and len(buyers) == 1:
            buyer = buyers[0]
            warnings.append("매수후보가 1건이라 자동 연결했습니다.")
        if buyer is None:
            raise ValueError("문서만으로 매수후보를 식별하지 못했습니다. 업로드 전에 매수후보를 선택해 주세요.")

    resolved_bid_type = bid_type or _extract_bid_type(source_text)
    if resolved_bid_type is None:
        raise ValueError("문서에서 입찰 유형을 식별하지 못했습니다. IOI/LOI/Final Offer 중 하나를 선택해 주세요.")

    amount, currency = _extract_amount(source_text)
    submitted_at = _extract_date_near_keywords(source_text, _SUBMITTED_AT_HINTS) or _extract_first_date(source_text)
    valid_until = _extract_date_near_keywords(source_text, _VALID_UNTIL_HINTS)
    valuation_method = _extract_valuation_method(source_text)
    multiple = _extract_multiple(source_text)

    inferred_fields: list[str] = ["buyer_candidate_id", "bid_type"]
    if amount is not None:
        inferred_fields.extend(["amount", "currency"])
    if submitted_at:
        inferred_fields.append("submitted_at")
    if valid_until:
        inferred_fields.append("valid_until")
    if valuation_method is not None:
        inferred_fields.append("valuation_method")
    if multiple is not None:
        inferred_fields.append("multiple")
    if parsed.parse_error:
        warnings.append("문서 본문 추출이 제한되어 파일명 중심으로 자동 기재했습니다.")

    return BidImportAnalysis(
        buyer=buyer,
        bid_type=resolved_bid_type,
        amount=amount,
        currency=currency,
        submitted_at=submitted_at,
        valid_until=valid_until,
        valuation_method=valuation_method,
        multiple=multiple,
        inferred_fields=inferred_fields,
        warnings=warnings,
    )


async def find_bid_import_target(
    db: AsyncSession,
    txn_id: uuid.UUID,
    buyer_candidate_id: uuid.UUID,
    bid_type: BidType,
) -> Bid | None:
    result = await db.execute(
        select(Bid)
        .where(
            Bid.transaction_id == txn_id,
            Bid.buyer_candidate_id == buyer_candidate_id,
            Bid.bid_type == bid_type,
        )
        .order_by(Bid.updated_at.desc(), Bid.created_at.desc())
    )
    bid = result.scalars().first()
    if bid is None:
        return None
    if any(
        (
            bid.amount is None,
            bid.submitted_at is None,
            bid.valid_until is None,
            bid.valuation_method is None,
            bid.multiple is None,
            not bid.notes,
        )
    ):
        return bid
    return None


def apply_analysis_to_bid(
    bid: Bid,
    analysis: BidImportAnalysis,
) -> tuple[dict[str, object | None], dict[str, object | None]]:
    update_data: dict[str, object | None] = {}
    old_value: dict[str, object | None] = {}

    field_map: tuple[tuple[str, object | None], ...] = (
        ("amount", analysis.amount),
        ("currency", analysis.currency if analysis.amount is not None else None),
        ("submitted_at", analysis.submitted_at),
        ("valid_until", analysis.valid_until),
        ("valuation_method", analysis.valuation_method),
        ("multiple", analysis.multiple),
    )

    for field_name, next_value in field_map:
        current_value = getattr(bid, field_name)
        if current_value is not None or next_value is None:
            continue
        old_value[field_name] = current_value
        setattr(bid, field_name, next_value)
        update_data[field_name] = next_value

    if not bid.notes:
        note = f"Imported from attachment: {analysis.bid_type.value} · {analysis.buyer.company_name}"
        old_value["notes"] = bid.notes
        bid.notes = note
        update_data["notes"] = note

    return old_value, update_data


async def sync_buyer_bid_snapshot(
    db: AsyncSession,
    txn_id: uuid.UUID,
    buyer_candidate_id: uuid.UUID,
) -> None:
    buyer = (
        await db.execute(
            select(BuyerCandidate).where(
                BuyerCandidate.transaction_id == txn_id,
                BuyerCandidate.id == buyer_candidate_id,
            )
        )
    ).scalar_one_or_none()
    if buyer is None:
        return

    bids = list(
        (
            await db.execute(
                select(Bid)
                .where(
                    Bid.transaction_id == txn_id,
                    Bid.buyer_candidate_id == buyer_candidate_id,
                )
                .order_by(Bid.created_at.desc())
            )
        ).scalars()
    )
    latest_by_type: dict[BidType, Bid] = {}
    for bid in bids:
        latest_by_type.setdefault(bid.bid_type, bid)

    ioi = latest_by_type.get(BidType.IOI)
    loi = latest_by_type.get(BidType.LOI)
    final_offer = latest_by_type.get(BidType.FINAL_OFFER)

    buyer.ioi_value = ioi.amount if ioi else None
    buyer.ioi_date = ioi.submitted_at if ioi else None
    buyer.loi_value = loi.amount if loi else None
    buyer.loi_date = loi.submitted_at if loi else None
    buyer.final_offer_value = final_offer.amount if final_offer else None
