"""Templates API - 템플릿 관리 엔드포인트.

EPIC-10: PPT/Word 템플릿 검증, 슬롯 탐지, CRUD 기능.
"""

import shutil
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi import UploadFile as FastAPIUploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.core.errors import ErrorCode
from app.core.exceptions import ValidationError
from app.database import get_db
from app.models.template import TemplateStatus
from app.schemas.template import (
    DetectedSlot,
    TemplateContract,
    TemplateCreate,
    TemplateListItem,
    TemplateRead,
    TemplateUpdate,
    TemplateValidationResult,
    ValidationIssue,
)
from app.services.template import template_service

router = APIRouter(prefix="/templates", tags=["templates"])


# =============================================================================
# Validation Endpoints
# =============================================================================


@router.post("/validate", response_model=TemplateValidationResult)
def validate_template(
    file: FastAPIUploadFile,
    template_type: Annotated[str, Query(pattern=r"^(pptx|docx)$")] = "pptx",
    expected_slots: Annotated[list[str] | None, Query()] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """템플릿 파일 검증.

    업로드된 템플릿 파일을 검증하고 슬롯을 탐지합니다.

    - **file**: PPTX 또는 DOCX 파일
    - **template_type**: 파일 타입 (pptx, docx)
    - **expected_slots**: 기대하는 슬롯 ID 목록 (선택)

    Returns:
        검증 결과 (탐지된 슬롯, 이슈, 생성된 계약)
    """
    # 임시 파일로 저장
    suffix = f".{template_type}"
    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        result = template_service.validate_template_file(
            file_path=tmp_path,
            template_type=template_type,
            expected_slots=expected_slots,
        )
        return result
    finally:
        # 임시 파일 삭제
        tmp_path.unlink(missing_ok=True)


@router.post("/validate-contract", response_model=list[ValidationIssue])
def validate_contract(
    contract: TemplateContract,
    current_user: CurrentUser = Depends(get_current_user),
):
    """템플릿 계약 검증.

    템플릿 계약 스키마가 유효한지 검증합니다.

    - **contract**: 검증할 템플릿 계약

    Returns:
        검증 이슈 목록 (빈 리스트면 유효)
    """
    return template_service.validate_template_contract(contract)


@router.post("/detect-slots", response_model=list[DetectedSlot])
def detect_slots(
    file: FastAPIUploadFile,
    template_type: Annotated[str, Query(pattern=r"^(pptx|docx)$")] = "pptx",
    current_user: CurrentUser = Depends(get_current_user),
):
    """템플릿 파일에서 슬롯 탐지.

    업로드된 템플릿 파일에서 슬롯을 탐지합니다.

    - **file**: PPTX 또는 DOCX 파일
    - **template_type**: 파일 타입

    Returns:
        탐지된 슬롯 목록
    """
    # 임시 파일로 저장
    suffix = f".{template_type}"
    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        if template_type == "pptx":
            slots = template_service.detect_slots_from_pptx(tmp_path)
        else:
            slots = template_service.detect_slots_from_docx(tmp_path)
        return slots
    finally:
        tmp_path.unlink(missing_ok=True)


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.post("", response_model=TemplateRead, status_code=201)
def create_template(
    template_data: TemplateCreate,
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
):
    """템플릿 생성.

    새로운 템플릿을 생성합니다.

    - **template_data**: 템플릿 생성 데이터

    Returns:
        생성된 템플릿
    """
    template = template_service.create_template(db, template_data)
    db.commit()
    return template_service.template_to_read(template)


@router.get("", response_model=list[TemplateListItem])
def list_templates(
    status: TemplateStatus | None = None,
    template_type: Annotated[str | None, Query(pattern=r"^(pptx|docx)$")] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """템플릿 목록 조회.

    템플릿 목록을 조회합니다.

    - **status**: 상태 필터 (선택)
    - **template_type**: 타입 필터 (선택)
    - **limit**: 최대 결과 수
    - **offset**: 시작 오프셋

    Returns:
        템플릿 목록
    """
    templates = template_service.list_templates(
        db, status=status, template_type=template_type, limit=limit, offset=offset
    )
    return [
        TemplateListItem(
            id=t.id,
            template_id=t.template_id,
            template_name=t.template_name,
            template_type=t.template_type.value,
            status=t.status,
            slot_count=len(t.contract.get("slots", [])),
            created_at=t.created_at,
        )
        for t in templates
    ]


@router.get("/{template_uuid}", response_model=TemplateRead)
def get_template(
    template_uuid: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """템플릿 조회.

    특정 템플릿을 조회합니다.

    - **template_uuid**: 템플릿 UUID

    Returns:
        템플릿 정보
    """
    template = template_service.get_template(db, template_uuid)
    return template_service.template_to_read(template)


@router.get("/by-id/{template_id}", response_model=TemplateRead)
def get_template_by_id(
    template_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """템플릿 조회 (template_id).

    template_id로 템플릿을 조회합니다.

    - **template_id**: 템플릿 ID

    Returns:
        템플릿 정보
    """
    template = template_service.get_template_by_template_id(db, template_id)
    return template_service.template_to_read(template)


@router.get("/{template_uuid}/slots", response_model=list)
def get_template_slots(
    template_uuid: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """템플릿 슬롯 목록 조회.

    특정 템플릿의 슬롯 목록을 조회합니다.

    - **template_uuid**: 템플릿 UUID

    Returns:
        슬롯 목록
    """
    template = template_service.get_template(db, template_uuid)
    return template.contract.get("slots", [])


@router.patch("/{template_uuid}", response_model=TemplateRead)
def update_template(
    template_uuid: uuid.UUID,
    update_data: TemplateUpdate,
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
):
    """템플릿 업데이트.

    템플릿 정보를 업데이트합니다.

    - **template_uuid**: 템플릿 UUID
    - **update_data**: 업데이트 데이터

    Returns:
        업데이트된 템플릿
    """
    template = template_service.update_template(db, template_uuid, update_data)
    db.commit()
    return template_service.template_to_read(template)


@router.delete("/{template_uuid}", status_code=204)
def delete_template(
    template_uuid: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
):
    """템플릿 삭제.

    템플릿을 삭제합니다.

    - **template_uuid**: 템플릿 UUID
    """
    template_service.delete_template(db, template_uuid)
    db.commit()


# =============================================================================
# Upload Endpoints
# =============================================================================


@router.post("/upload", response_model=TemplateRead, status_code=201)
def upload_template(
    file: FastAPIUploadFile,
    template_name: str = Query(..., min_length=1, max_length=255),
    description: str | None = Query(default=None, max_length=1000),
    template_type: Annotated[str, Query(pattern=r"^(pptx|docx)$")] = "pptx",
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
):
    """템플릿 업로드.

    템플릿 파일을 업로드하고 등록합니다.

    - **file**: PPTX 또는 DOCX 파일
    - **template_name**: 템플릿 이름
    - **description**: 설명 (선택)
    - **template_type**: 파일 타입

    Returns:
        생성된 템플릿
    """
    # 확장자 검증
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    expected_ext = f".{template_type}"
    if ext != expected_ext:
        raise ValidationError(
            ErrorCode.TEMPLATE_FILE_INVALID,
            f"Expected {expected_ext} file, got {ext}",
        )

    # 저장 디렉토리 생성
    upload_dir = Path("uploads/templates")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 파일 저장
    file_id = uuid.uuid4().hex[:12]
    file_path = upload_dir / f"{file_id}{ext}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 파일 검증 및 계약 생성
    validation_result = template_service.validate_template_file(
        file_path=file_path,
        template_type=template_type,
    )

    if not validation_result.is_valid:
        # 검증 실패 시 파일 삭제
        file_path.unlink(missing_ok=True)
        error_msgs = [
            i.message for i in validation_result.issues if i.severity == "error"
        ]
        raise ValidationError(
            ErrorCode.TEMPLATE_VALIDATION_FAILED,
            f"Template validation failed: {'; '.join(error_msgs)}",
        )

    # 계약이 없으면 기본 계약 생성
    if not validation_result.contract:
        file_path.unlink(missing_ok=True)
        raise ValidationError(
            ErrorCode.TEMPLATE_CONTRACT_INVALID,
            "Failed to generate template contract",
        )

    # 템플릿 이름과 설명 업데이트
    contract = validation_result.contract
    contract.template_name = template_name

    # 템플릿 생성
    template_data = TemplateCreate(
        template_name=template_name,
        template_type=template_type,
        contract=contract,
        description=description,
    )

    template = template_service.create_template(db, template_data, file_path=file_path)
    db.commit()

    return template_service.template_to_read(template)


@router.post("/{template_uuid}/activate", response_model=TemplateRead)
def activate_template(
    template_uuid: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
):
    """템플릿 활성화.

    템플릿을 활성화 상태로 변경합니다.

    - **template_uuid**: 템플릿 UUID

    Returns:
        업데이트된 템플릿
    """
    from app.schemas.template import TemplateStatus as SchemaTemplateStatus

    update_data = TemplateUpdate(status=SchemaTemplateStatus.ACTIVE)
    template = template_service.update_template(db, template_uuid, update_data)
    db.commit()
    return template_service.template_to_read(template)


@router.post("/{template_uuid}/archive", response_model=TemplateRead)
def archive_template(
    template_uuid: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
):
    """템플릿 아카이브.

    템플릿을 아카이브 상태로 변경합니다.

    - **template_uuid**: 템플릿 UUID

    Returns:
        업데이트된 템플릿
    """
    from app.schemas.template import TemplateStatus as SchemaTemplateStatus

    update_data = TemplateUpdate(status=SchemaTemplateStatus.ARCHIVED)
    template = template_service.update_template(db, template_uuid, update_data)
    db.commit()
    return template_service.template_to_read(template)
