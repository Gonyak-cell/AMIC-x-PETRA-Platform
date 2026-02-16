"""VDR (Virtual Data Room) API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.audit import AuditAction, AuditLog
from app.models.deal import Deal
from app.models.upload import UploadFile
from app.models.vdr import VdrFolder, VdrFolderType
from app.schemas.upload import UploadFileRead
from app.schemas.vdr import (
    VdrFolderCreate,
    VdrFolderRead,
    VdrFolderTree,
    VdrFolderUpdate,
    VdrInitRequest,
)

router = APIRouter(prefix="/deals/{deal_id}/vdr", tags=["vdr"])

# Default folders to initialize with VDR
_DEFAULT_FOLDERS: list[tuple[VdrFolderType, str, bool]] = [
    (VdrFolderType.FINANCIAL_STATEMENTS, "Financial Statements", True),
    (VdrFolderType.ACCOUNTS_RECEIVABLE, "Accounts Receivable", False),
    (VdrFolderType.ACCOUNTS_PAYABLE, "Accounts Payable", False),
    (VdrFolderType.BANK_DEBT, "Bank Debt", False),
    (VdrFolderType.LEASE, "Lease", False),
    (VdrFolderType.OTHERS, "Others", False),
]


def _build_folder_tree(
    folders: list[VdrFolder],
    db: Session,
) -> list[VdrFolderTree]:
    """Convert flat folder list to hierarchical VdrFolderTree objects.

    Args:
        folders: Flat list of VdrFolder ORM objects.
        db: Database session for file count queries.

    Returns:
        List of root-level VdrFolderTree with nested children.
    """
    # Build lookup by id
    folder_map: dict[UUID, VdrFolderTree] = {}
    for folder in folders:
        file_count = (
            db.scalar(
                select(func.count())
                .select_from(UploadFile)
                .where(
                    UploadFile.vdr_folder_id == folder.id,
                )
            )
            or 0
        )
        tree_node = VdrFolderTree.model_validate(folder)
        tree_node.file_count = file_count
        tree_node.children = []
        folder_map[folder.id] = tree_node

    # Build tree
    roots: list[VdrFolderTree] = []
    for folder in folders:
        node = folder_map[folder.id]
        if folder.parent_id and folder.parent_id in folder_map:
            folder_map[folder.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots


@router.post("/init", response_model=list[VdrFolderRead], status_code=201)
def init_vdr_folders(
    deal_id: UUID,
    body: VdrInitRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initialize default VDR folder structure for a deal.

    Creates the 6 standard folders: FINANCIAL_STATEMENTS (required),
    ACCOUNTS_RECEIVABLE, ACCOUNTS_PAYABLE, BANK_DEBT, LEASE, OTHERS.

    Args:
        deal_id: Deal UUID.
        body: Init options.

    Returns:
        List of created VDR folders.
    """
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Check if folders already exist
    existing = db.scalar(
        select(func.count())
        .select_from(VdrFolder)
        .where(
            VdrFolder.deal_id == deal_id,
        )
    )
    if existing and existing > 0:
        raise HTTPException(
            status_code=400,
            detail="VDR folders already initialized for this deal",
        )

    created_folders: list[VdrFolder] = []
    for idx, (folder_type, name, is_required) in enumerate(_DEFAULT_FOLDERS):
        folder = VdrFolder(
            deal_id=deal_id,
            name=name,
            folder_type=folder_type,
            order_index=idx,
            is_required=is_required,
        )
        db.add(folder)
        created_folders.append(folder)

    db.flush()

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="vdr_folder",
            entity_id=deal_id,
            action=AuditAction.CREATE,
            actor=current_user.email,
            new_value={"action": "init", "folder_count": len(created_folders)},
        )
    )

    db.commit()
    for folder in created_folders:
        db.refresh(folder)
    return created_folders


@router.get("/folders", response_model=list[VdrFolderTree])
def list_vdr_folders(
    deal_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List VDR folder tree for a deal.

    Args:
        deal_id: Deal UUID.

    Returns:
        Hierarchical folder tree with file counts.
    """
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    stmt = (
        select(VdrFolder)
        .where(VdrFolder.deal_id == deal_id)
        .order_by(VdrFolder.order_index)
    )
    folders = list(db.scalars(stmt).all())
    return _build_folder_tree(folders, db)


@router.post("/folders", response_model=VdrFolderRead, status_code=201)
def create_vdr_folder(
    deal_id: UUID,
    body: VdrFolderCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new VDR folder.

    Args:
        deal_id: Deal UUID.
        body: Folder creation data.

    Returns:
        Created folder.
    """
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Validate parent_id if provided
    if body.parent_id is not None:
        parent = db.get(VdrFolder, body.parent_id)
        if parent is None or parent.deal_id != deal_id:
            raise HTTPException(status_code=404, detail="Parent folder not found")

    # Determine next order_index
    max_order = db.scalar(
        select(func.max(VdrFolder.order_index)).where(
            VdrFolder.deal_id == deal_id,
            VdrFolder.parent_id == body.parent_id,
        )
    )
    next_order = (max_order or 0) + 1

    folder = VdrFolder(
        deal_id=deal_id,
        name=body.name,
        folder_type=body.folder_type,
        parent_id=body.parent_id,
        is_required=body.is_required,
        order_index=next_order,
    )
    db.add(folder)
    db.flush()

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="vdr_folder",
            entity_id=folder.id,
            action=AuditAction.CREATE,
            actor=current_user.email,
            new_value=body.model_dump(mode="json"),
        )
    )

    db.commit()
    db.refresh(folder)
    return folder


@router.put("/folders/{folder_id}", response_model=VdrFolderRead)
def update_vdr_folder(
    deal_id: UUID,
    folder_id: UUID,
    body: VdrFolderUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a VDR folder.

    Args:
        deal_id: Deal UUID.
        folder_id: Folder UUID.
        body: Fields to update.

    Returns:
        Updated folder.
    """
    folder = db.get(VdrFolder, folder_id)
    if folder is None or folder.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Folder not found")

    _UPDATABLE_FIELDS = {"name", "order_index"}
    old_values = {}
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key not in _UPDATABLE_FIELDS:
            continue
        old_values[key] = getattr(folder, key)
        setattr(folder, key, value)

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="vdr_folder",
            entity_id=folder.id,
            action=AuditAction.UPDATE,
            actor=current_user.email,
            old_value=old_values,
            new_value=update_data,
        )
    )

    db.commit()
    db.refresh(folder)
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
def delete_vdr_folder(
    deal_id: UUID,
    folder_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a VDR folder.

    Args:
        deal_id: Deal UUID.
        folder_id: Folder UUID.
    """
    folder = db.get(VdrFolder, folder_id)
    if folder is None or folder.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Folder not found")

    if folder.is_required:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a required folder",
        )

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="vdr_folder",
            entity_id=folder.id,
            action=AuditAction.DELETE,
            actor=current_user.email,
            old_value={"name": folder.name, "folder_type": folder.folder_type.value},
        )
    )

    db.delete(folder)
    db.commit()


@router.get("/folders/{folder_id}/files", response_model=list[UploadFileRead])
def list_folder_files(
    deal_id: UUID,
    folder_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List files in a VDR folder.

    Args:
        deal_id: Deal UUID.
        folder_id: Folder UUID.

    Returns:
        List of upload files in the folder.
    """
    folder = db.get(VdrFolder, folder_id)
    if folder is None or folder.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Folder not found")

    stmt = (
        select(UploadFile)
        .where(UploadFile.vdr_folder_id == folder_id)
        .order_by(UploadFile.created_at.desc())
    )
    return list(db.scalars(stmt).all())
