"""RBAC 권한 정의 및 검사 — FDD-1701.

역할 기반 접근 제어 v1.
"""

from enum import StrEnum

from app.models.user import UserRole


class Permission(StrEnum):
    DEAL_CREATE = "deal:create"
    DEAL_READ = "deal:read"
    DEAL_UPDATE = "deal:update"
    DEAL_DELETE = "deal:delete"
    DEFINITION_APPROVE = "definition:approve"
    UPLOAD_CREATE = "upload:create"
    MAPPING_APPROVE = "mapping:approve"
    REPORT_GENERATE = "report:generate"
    REPORT_DOWNLOAD = "report:download"
    AUDIT_VIEW = "audit:view"
    USER_MANAGE = "user:manage"

    # Phase 5: Portal endpoints
    NOTIFICATION_READ = "notification:read"
    EXPORT_READ = "export:read"
    EXPORT_DELETE = "export:delete"
    WEBHOOK_MANAGE = "webhook:manage"
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"

    # Client role: 배정된 딜만 읽기
    DEAL_READ_ASSIGNED = "deal:read_assigned"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: set(Permission),
    UserRole.MANAGER: {
        Permission.DEAL_CREATE,
        Permission.DEAL_READ,
        Permission.DEAL_UPDATE,
        Permission.DEAL_DELETE,
        Permission.DEFINITION_APPROVE,
        Permission.UPLOAD_CREATE,
        Permission.MAPPING_APPROVE,
        Permission.REPORT_GENERATE,
        Permission.REPORT_DOWNLOAD,
        Permission.AUDIT_VIEW,
        Permission.NOTIFICATION_READ,
        Permission.EXPORT_READ,
        Permission.EXPORT_DELETE,
        Permission.SETTINGS_READ,
        Permission.SETTINGS_UPDATE,
    },
    UserRole.ANALYST: {
        Permission.DEAL_READ,
        Permission.DEAL_UPDATE,
        Permission.UPLOAD_CREATE,
        Permission.REPORT_GENERATE,
        Permission.REPORT_DOWNLOAD,
        Permission.NOTIFICATION_READ,
        Permission.EXPORT_READ,
        Permission.SETTINGS_READ,
        Permission.SETTINGS_UPDATE,
    },
    UserRole.VIEWER: {
        Permission.DEAL_READ,
        Permission.REPORT_DOWNLOAD,
        Permission.NOTIFICATION_READ,
        Permission.SETTINGS_READ,
    },
    UserRole.CLIENT: {
        Permission.DEAL_READ_ASSIGNED,
        Permission.NOTIFICATION_READ,
        Permission.SETTINGS_READ,
        Permission.SETTINGS_UPDATE,
    },
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    """역할이 해당 권한을 보유하는지 확인한다."""
    return permission in ROLE_PERMISSIONS.get(role, set())


def get_permissions(role: UserRole) -> set[Permission]:
    """역할의 전체 권한 목록을 반환한다."""
    return ROLE_PERMISSIONS.get(role, set())
