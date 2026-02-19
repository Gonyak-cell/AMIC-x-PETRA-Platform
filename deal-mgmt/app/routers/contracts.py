"""계약/SPA 관리 라우터 — 계약서 + 버전 + AI 분석."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.contract import Contract
from app.models.contract_version import ContractVersion
from app.models.enums import AuditAction, ContractStatus, SignatureStatus
from app.schemas.contract import (
    AIAnalysisResult,
    ContractCreate,
    ContractOut,
    ContractSummary,
    ContractUpdate,
    ContractVersionCreate,
    ContractVersionOut,
)
from app.services import audit_service, contract_analysis_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/contracts", tags=["Contracts"])


@router.get("", response_model=list[ContractOut])
async def list_contracts(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(Contract).where(Contract.transaction_id == txn_id).order_by(Contract.created_at.desc())
    result = await db.execute(q)
    return [ContractOut.model_validate(c) for c in result.scalars().all()]


@router.get("/summary", response_model=ContractSummary)
async def contract_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(Contract).where(Contract.transaction_id == txn_id)
    result = await db.execute(q)
    contracts = list(result.scalars().all())

    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    pending_sigs = 0
    executed = 0
    for c in contracts:
        by_type[c.contract_type.value] = by_type.get(c.contract_type.value, 0) + 1
        by_status[c.status.value] = by_status.get(c.status.value, 0) + 1
        if c.seller_signature == SignatureStatus.PENDING or c.buyer_signature == SignatureStatus.PENDING:
            pending_sigs += 1
        if c.status == ContractStatus.FULLY_EXECUTED:
            executed += 1

    return ContractSummary(
        total=len(contracts),
        by_type=by_type,
        by_status=by_status,
        pending_signatures=pending_sigs,
        fully_executed=executed,
    )


@router.post("", response_model=ContractOut, status_code=201)
async def create_contract(
    txn_id: uuid.UUID,
    body: ContractCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    contract = Contract(transaction_id=txn_id, **body.model_dump())
    db.add(contract)
    await db.flush()
    await audit_service.record(
        db, entity_type="Contract", entity_id=contract.id,
        action=AuditAction.CREATE, actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(contract)
    return ContractOut.model_validate(contract)


@router.patch("/{contract_id}", response_model=ContractOut)
async def update_contract(
    txn_id: uuid.UUID,
    contract_id: uuid.UUID,
    body: ContractUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(Contract).where(Contract.id == contract_id, Contract.transaction_id == txn_id)
    contract = (await db.execute(q)).scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="계약서를 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(contract, k, v)
    await audit_service.record(
        db, entity_type="Contract", entity_id=contract.id,
        action=AuditAction.UPDATE, actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(contract)
    return ContractOut.model_validate(contract)


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    txn_id: uuid.UUID,
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(Contract).where(Contract.id == contract_id, Contract.transaction_id == txn_id)
    contract = (await db.execute(q)).scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="계약서를 찾을 수 없습니다")
    await audit_service.record(
        db, entity_type="Contract", entity_id=contract.id,
        action=AuditAction.DELETE, actor_email=claims.email,
    )
    await db.delete(contract)
    await db.commit()


# ── Versions ──────────────────────────────────────────────


@router.get("/{contract_id}/versions", response_model=list[ContractVersionOut])
async def list_versions(
    txn_id: uuid.UUID,
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    # 계약 존재 확인
    cq = select(Contract).where(Contract.id == contract_id, Contract.transaction_id == txn_id)
    if (await db.execute(cq)).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="계약서를 찾을 수 없습니다")

    q = (
        select(ContractVersion)
        .where(ContractVersion.contract_id == contract_id)
        .order_by(ContractVersion.version_number.desc())
    )
    result = await db.execute(q)
    return [ContractVersionOut.model_validate(v) for v in result.scalars().all()]


@router.post("/{contract_id}/versions", response_model=ContractVersionOut, status_code=201)
async def create_version(
    txn_id: uuid.UUID,
    contract_id: uuid.UUID,
    body: ContractVersionCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    cq = select(Contract).where(Contract.id == contract_id, Contract.transaction_id == txn_id)
    contract = (await db.execute(cq)).scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="계약서를 찾을 수 없습니다")

    # 버전 번호 자동 증가
    contract.current_version += 1
    contract.document_url = body.document_url

    version = ContractVersion(
        contract_id=contract_id,
        version_number=contract.current_version,
        **body.model_dump(),
    )
    db.add(version)
    await db.flush()
    await audit_service.record(
        db, entity_type="ContractVersion", entity_id=version.id,
        action=AuditAction.CREATE, actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(version)
    return ContractVersionOut.model_validate(version)


# ── AI Analysis ───────────────────────────────────────────


@router.post("/{contract_id}/analyze", response_model=AIAnalysisResult)
async def analyze_contract(
    txn_id: uuid.UUID,
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    cq = select(Contract).where(Contract.id == contract_id, Contract.transaction_id == txn_id)
    contract = (await db.execute(cq)).scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="계약서를 찾을 수 없습니다")

    result = await contract_analysis_service.analyze_contract(contract.id, contract.document_url)

    # AI 결과를 계약서에 저장
    contract.ai_analysis_summary = result.message
    contract.ai_risk_flags = [flag.model_dump() for flag in result.clauses] if result.clauses else None
    await db.commit()

    return result
