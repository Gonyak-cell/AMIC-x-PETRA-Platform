"""RBAC 권한 체계 유닛 테스트."""

from app.auth.rbac import ROLE_PERMISSIONS, Permission, get_permissions, has_permission
from app.models.user import UserRole


class TestRBAC:
    def test_admin_has_all_permissions(self):
        for perm in Permission:
            assert has_permission(UserRole.ADMIN, perm) is True

    def test_admin_permission_count(self):
        perms = get_permissions(UserRole.ADMIN)
        assert len(perms) == len(Permission)

    def test_manager_has_deal_crud(self):
        assert has_permission(UserRole.MANAGER, Permission.DEAL_CREATE) is True
        assert has_permission(UserRole.MANAGER, Permission.DEAL_READ) is True
        assert has_permission(UserRole.MANAGER, Permission.DEAL_UPDATE) is True
        assert has_permission(UserRole.MANAGER, Permission.DEAL_DELETE) is True

    def test_manager_can_approve(self):
        assert has_permission(UserRole.MANAGER, Permission.DEFINITION_APPROVE) is True
        assert has_permission(UserRole.MANAGER, Permission.MAPPING_APPROVE) is True

    def test_manager_cannot_manage_users(self):
        assert has_permission(UserRole.MANAGER, Permission.USER_MANAGE) is False

    def test_analyst_can_read_and_update(self):
        assert has_permission(UserRole.ANALYST, Permission.DEAL_READ) is True
        assert has_permission(UserRole.ANALYST, Permission.DEAL_UPDATE) is True

    def test_analyst_cannot_create_deal(self):
        assert has_permission(UserRole.ANALYST, Permission.DEAL_CREATE) is False

    def test_analyst_cannot_approve(self):
        assert has_permission(UserRole.ANALYST, Permission.DEFINITION_APPROVE) is False
        assert has_permission(UserRole.ANALYST, Permission.MAPPING_APPROVE) is False

    def test_viewer_can_only_read_and_download(self):
        perms = get_permissions(UserRole.VIEWER)
        assert perms == {
            Permission.DEAL_READ,
            Permission.REPORT_DOWNLOAD,
            Permission.NOTIFICATION_READ,
            Permission.SETTINGS_READ,
        }

    def test_viewer_cannot_create_deal(self):
        assert has_permission(UserRole.VIEWER, Permission.DEAL_CREATE) is False

    def test_viewer_cannot_upload(self):
        assert has_permission(UserRole.VIEWER, Permission.UPLOAD_CREATE) is False

    def test_all_roles_defined(self):
        for role in UserRole:
            assert role in ROLE_PERMISSIONS
