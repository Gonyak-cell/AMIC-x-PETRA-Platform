"""CoA 매핑 엔진 — FDD-302.

원천 계정명(TB account_name)을 표준 라인아이템(StandardLineItem)에 대응시킨다.
알고리즘 우선순위: exact → keyword → fuzzy.
LLM 기반 매핑은 Sprint 6에서 추가 예정.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models.account_mapping import (
    AccountMapping,
    MappingConfidence,
    MappingStatus,
)
from app.models.audit import AuditAction, AuditLog
from app.models.standard_line_item import StandardLineItem
from app.schemas.mapping import AccountMappingCreate, MappingSuggestion

# ── Pure matching functions ──────────────────────────────


def _normalize(name: str) -> str:
    """공백 제거 + 소문자 변환."""
    return name.strip().lower()


def _exact_match(
    source_name: str,
    line_items: list[StandardLineItem],
) -> tuple[StandardLineItem, Decimal] | None:
    """정확 매칭: name_ko 또는 name_en 일치."""
    normalized = _normalize(source_name)
    for item in line_items:
        if normalized in (_normalize(item.name_ko), _normalize(item.name_en)):
            return item, Decimal("100.00")
    return None


def _keyword_match(
    source_name: str,
    line_items: list[StandardLineItem],
) -> tuple[StandardLineItem, Decimal] | None:
    """키워드 매칭: keywords 필드의 키워드가 source_name에 포함."""
    normalized = _normalize(source_name)
    best_item: StandardLineItem | None = None
    best_keyword_len = 0

    for item in line_items:
        if not item.keywords:
            continue
        for keyword in item.keywords:
            kw = _normalize(keyword)
            if kw and kw in normalized and len(kw) > best_keyword_len:
                best_keyword_len = len(kw)
                best_item = item

    if best_item is not None:
        return best_item, Decimal("75.00")
    return None


def _fuzzy_match(
    source_name: str,
    line_items: list[StandardLineItem],
    threshold: Decimal = Decimal("50.0"),
) -> tuple[StandardLineItem, Decimal] | None:
    """Fuzzy 매칭: SequenceMatcher 유사도 비교."""
    normalized = _normalize(source_name)
    best_item: StandardLineItem | None = None
    best_score = Decimal("0")

    for item in line_items:
        for target_name in (item.name_ko, item.name_en):
            ratio = SequenceMatcher(None, normalized, _normalize(target_name)).ratio()
            score = Decimal(str(round(ratio * 100, 2)))
            if score > best_score and score >= threshold:
                best_score = score
                best_item = item

    if best_item is not None:
        return best_item, best_score
    return None


def _score_to_confidence(score: Decimal) -> MappingConfidence:
    """점수를 신뢰도로 변환."""
    if score >= Decimal("90"):
        return MappingConfidence.HIGH
    if score >= Decimal("70"):
        return MappingConfidence.MEDIUM
    return MappingConfidence.LOW


# ── Public API ───────────────────────────────────────────


def suggest_mappings(
    line_items: list[StandardLineItem],
    tb_accounts: list[tuple[str, str, Decimal]],
) -> list[MappingSuggestion]:
    """매핑 제안을 생성한다 (순수 함수, DB 접근 없음).

    Args:
        line_items: 표준 라인아이템 목록 (DB에서 미리 조회).
        tb_accounts: [(account_code, account_name, balance), ...] TB 계정 목록.

    Returns:
        MappingSuggestion 목록 (unmapped 포함).
    """
    suggestions: list[MappingSuggestion] = []

    for acct_code, acct_name, balance in tb_accounts:
        # 1. Exact match
        result = _exact_match(acct_name, line_items)
        if result:
            item, score = result
            suggestions.append(
                MappingSuggestion(
                    source_account_code=acct_code,
                    source_account_name=acct_name,
                    suggested_target_code=item.code,
                    suggested_target_name_en=item.name_en,
                    suggested_target_name_ko=item.name_ko,
                    confidence=MappingConfidence.HIGH,
                    match_score=score,
                    algorithm="exact",
                    affected_amount=balance,
                )
            )
            continue

        # 2. Keyword match
        result = _keyword_match(acct_name, line_items)
        if result:
            item, score = result
            suggestions.append(
                MappingSuggestion(
                    source_account_code=acct_code,
                    source_account_name=acct_name,
                    suggested_target_code=item.code,
                    suggested_target_name_en=item.name_en,
                    suggested_target_name_ko=item.name_ko,
                    confidence=MappingConfidence.MEDIUM,
                    match_score=score,
                    algorithm="keyword",
                    affected_amount=balance,
                )
            )
            continue

        # 3. Fuzzy match
        result = _fuzzy_match(acct_name, line_items)
        if result:
            item, score = result
            suggestions.append(
                MappingSuggestion(
                    source_account_code=acct_code,
                    source_account_name=acct_name,
                    suggested_target_code=item.code,
                    suggested_target_name_en=item.name_en,
                    suggested_target_name_ko=item.name_ko,
                    confidence=_score_to_confidence(score),
                    match_score=score,
                    algorithm="fuzzy",
                    affected_amount=balance,
                )
            )
            continue

        # 4. Unmapped
        suggestions.append(
            MappingSuggestion(
                source_account_code=acct_code,
                source_account_name=acct_name,
                suggested_target_code="",
                suggested_target_name_en="",
                suggested_target_name_ko="",
                confidence=MappingConfidence.UNMAPPED,
                match_score=Decimal("0"),
                algorithm="none",
                affected_amount=balance,
            )
        )

    return suggestions


def save_mappings(
    db: Session,
    deal_id: uuid.UUID,
    mappings: list[AccountMappingCreate],
) -> list[AccountMapping]:
    """매핑을 DB에 저장 + AuditLog 기록.

    Args:
        db: DB 세션.
        deal_id: 딜 ID.
        mappings: 저장할 매핑 목록.

    Returns:
        저장된 AccountMapping 목록.
    """
    saved: list[AccountMapping] = []

    for m in mappings:
        mapping = AccountMapping(
            deal_id=deal_id,
            source_account_code=m.source_account_code,
            source_account_name=m.source_account_name,
            target_line_item_code=m.target_line_item_code,
            confidence=m.confidence,
            status=m.status,
            match_score=m.match_score,
            algorithm=m.algorithm,
            affected_amount=m.affected_amount,
        )
        db.add(mapping)
        saved.append(mapping)

    db.flush()

    for mapping in saved:
        db.add(
            AuditLog(
                deal_id=deal_id,
                entity_type="account_mapping",
                entity_id=mapping.id,
                action=AuditAction.CREATE,
                actor="system",
                new_value={
                    "source": mapping.source_account_code,
                    "target": mapping.target_line_item_code,
                    "confidence": mapping.confidence.value,
                },
            )
        )

    db.commit()
    return saved


def approve_mapping(
    db: Session,
    mapping: AccountMapping,
    approved_by: str,
) -> AccountMapping:
    """매핑을 승인한다 + AuditLog 기록."""
    old_status = mapping.status.value
    mapping.status = MappingStatus.APPROVED
    mapping.approved_by = approved_by
    mapping.approved_at = datetime.now(UTC)

    db.flush()

    db.add(
        AuditLog(
            deal_id=mapping.deal_id,
            entity_type="account_mapping",
            entity_id=mapping.id,
            action=AuditAction.APPROVE,
            actor=approved_by,
            old_value={"status": old_status},
            new_value={"status": "APPROVED"},
        )
    )

    db.commit()
    db.refresh(mapping)
    return mapping
