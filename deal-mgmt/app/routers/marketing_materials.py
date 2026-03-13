"""마케팅 자료 라우터 — TM / DM / IM CRUD + 다운로드."""

from __future__ import annotations

import unicodedata
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DocumentNotFoundError
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import MarketingDocStatus
from app.schemas.marketing_material import (
    DistributionUpdate,
    MarketingMaterialCreate,
    MarketingMaterialOut,
)
from app.services import marketing_material_service, transaction_service

router = APIRouter(
    prefix="/transactions/{txn_id}/marketing-materials",
    tags=["Marketing Materials"],
)

# 경로 탐색(Path Traversal) 방어
_SAFE_OUTPUT_DIR = (Path(__file__).resolve().parent.parent.parent / "generated" / "memorandum").resolve()


async def _get_and_authorize_txn(
    db: AsyncSession,
    txn_id: uuid.UUID,
    claims: JWTClaims,
):
    """거래 존재 확인 및 접근 권한 검증."""
    try:
        txn = await transaction_service.get_transaction(db, txn_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="거래를 찾을 수 없습니다.")
    # CLIENT 역할: deal_clients 테이블 기반 접근 제어
    if claims.role == "CLIENT":
        await check_client_deal_access(db, txn_id, claims)
        return txn
    if (
        claims.role != "ADMIN"
        and claims.email is not None
        and txn.lead_advisor_email != claims.email
        and txn.deal_captain_email != claims.email
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 거래에 접근할 권한이 없습니다",
        )
    return txn


# ── 목록 조회 ──────────────────────────────────────────────────


@router.get("", response_model=list[MarketingMaterialOut])
async def list_marketing_materials(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await _get_and_authorize_txn(db, txn_id, claims)
    return await marketing_material_service.list_marketing_materials(db, txn_id)


# ── 생성 ───────────────────────────────────────────────────────


@router.post("", response_model=MarketingMaterialOut, status_code=status.HTTP_201_CREATED)
async def create_marketing_material(
    txn_id: uuid.UUID,
    body: MarketingMaterialCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """마케팅 자료를 생성하고 PPTX 생성을 트리거한다.

    - TM, DM, IM 모두 memo_generator.py 기반 PPTX 출력.
    - `parameters`에 content JSON을 넣으면 맞춤 슬라이드 생성.
    - 없으면 기본 플레이스홀더 템플릿 사용.
    """
    await _get_and_authorize_txn(db, txn_id, claims)
    if body.enable_ralph_loop:
        return await marketing_material_service.create_marketing_material_with_ralph(
            db, txn_id, body, created_by_email=claims.email
        )
    return await marketing_material_service.create_marketing_material(db, txn_id, body, created_by_email=claims.email)


# ── 단건 조회 ──────────────────────────────────────────────────


@router.get("/{mat_id}", response_model=MarketingMaterialOut)
async def get_marketing_material(
    txn_id: uuid.UUID,
    mat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        return await marketing_material_service.get_marketing_material(db, txn_id, mat_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── 재생성 ────────────────────────────────────────────────────


@router.post("/{mat_id}/regenerate", response_model=MarketingMaterialOut)
async def regenerate_marketing_material(
    txn_id: uuid.UUID,
    mat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """실패한 자료를 재생성한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        return await marketing_material_service.generate_marketing_material(db, txn_id, mat_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── 배포 업데이트 ─────────────────────────────────────────────


@router.put("/{mat_id}/distribute", response_model=MarketingMaterialOut)
async def update_distribution(
    txn_id: uuid.UUID,
    mat_id: uuid.UUID,
    body: DistributionUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """배포 대상 목록을 갱신한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        return await marketing_material_service.update_distribution(db, txn_id, mat_id, body)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── 다운로드 ──────────────────────────────────────────────────


@router.get("/{mat_id}/download")
async def download_marketing_material(
    txn_id: uuid.UUID,
    mat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """생성된 PPTX 파일을 다운로드한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        mat = await marketing_material_service.get_marketing_material(db, txn_id, mat_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if mat.status not in (MarketingDocStatus.READY, MarketingDocStatus.CONDITIONAL_READY) or not mat.file_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"파일이 아직 준비되지 않았습니다. 현재 상태: {mat.status}",
        )

    # 경로 탐색 방어
    file_path = Path(mat.file_path).resolve()
    if not str(file_path).startswith(str(_SAFE_OUTPUT_DIR)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="유효하지 않은 파일 경로입니다.")

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="파일이 존재하지 않습니다.")

    type_label = mat.doc_type.value  # TM / DM / IM
    # 제어문자·경로구분자만 제거 (한글 등 유니코드 허용)
    safe_title = "".join(c for c in mat.title if unicodedata.category(c) not in ("Cc", "Cs") and c not in r'/\:*?"<>|')[
        :50
    ].strip()
    download_name = f"{type_label}_{safe_title}.pptx"

    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=download_name,
    )


# ── 삭제 ─────────────────────────────────────────────────────


@router.delete("/{mat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_marketing_material(
    txn_id: uuid.UUID,
    mat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        await marketing_material_service.delete_marketing_material(db, txn_id, mat_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
