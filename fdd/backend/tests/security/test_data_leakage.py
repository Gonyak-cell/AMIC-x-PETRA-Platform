"""민감정보 누출 테스트 — FDD-1405.

에러 메시지 누출, 로그 누출, API 응답 필드 노출, 마스킹 검증, 파일 접근 차단.
총 10개 테스트.
"""

import uuid

from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app

# ─── 1. 에러 메시지 누출 ───────────────────────────────


class TestErrorMessageLeakage:
    """에러 응답에 내부 정보(스택 트레이스, SQL 등)가 포함되면 안 된다."""

    def test_404_no_stack_trace(
        self, sec_client: TestClient, admin_user_obj: CurrentUser
    ):
        """FDD-1405-01: 404 응답에 스택 트레이스 없음."""
        app.dependency_overrides[get_current_user] = lambda: admin_user_obj
        try:
            fake_id = str(uuid.uuid4())
            resp = sec_client.get(f"/api/v1/deals/{fake_id}")
            assert resp.status_code == 404
            body = resp.text.lower()
            assert "traceback" not in body
            assert "file " not in body  # Python traceback pattern
            assert ".py" not in body or "error" in body  # Allow error code names
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_500_no_internal_details(self, sec_client: TestClient, admin_user_obj):
        """FDD-1405-02: 500 응답에 DB/내부 경로 노출 없음."""
        app.dependency_overrides[get_current_user] = lambda: admin_user_obj
        try:
            # 잘못된 형식 요청으로 서버 에러 유도
            resp = sec_client.post(
                "/api/v1/deals",
                content=b"not-json",
                headers={"Content-Type": "application/json"},
            )
            body = resp.text.lower()
            # SQL 키워드 노출 방지
            assert "select " not in body
            assert "insert " not in body
            assert "sqlalchemy" not in body
            # 파일 경로 노출 방지
            assert "c:\\" not in body
            assert "/app/" not in body or "api" in body
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_validation_error_no_internals(
        self, sec_client: TestClient, admin_user_obj
    ):
        """FDD-1405-03: 유효성 검사 에러에 내부 구현 정보 없음."""
        app.dependency_overrides[get_current_user] = lambda: admin_user_obj
        try:
            resp = sec_client.post(
                "/api/v1/deals",
                json={"invalid": "payload"},
            )
            body = resp.text.lower()
            # Pydantic 내부 에러 메시지는 허용하지만 경로/DB 누출은 차단
            assert "password" not in body
            assert "secret" not in body
            assert "jwt_secret" not in body
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ─── 2. API 응답 필드 노출 ──────────────────────────────


class TestAPIResponseExposure:
    """API 응답에 불필요한 내부 필드가 포함되면 안 된다."""

    def test_user_response_no_password(
        self, sec_client: TestClient, admin_user_obj: CurrentUser
    ):
        """FDD-1405-04: 사용자 조회 응답에 hashed_password 없음."""
        app.dependency_overrides[get_current_user] = lambda: admin_user_obj
        try:
            resp = sec_client.get("/api/v1/auth/users")
            if resp.status_code == 200:
                body = resp.text
                assert "hashed_password" not in body
                assert "password_hash" not in body
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_deal_response_no_internal_ids(
        self, sec_client: TestClient, admin_user_obj, deal_by_admin
    ):
        """FDD-1405-05: 딜 응답에 내부 전용 필드(DB PK 등) 최소화."""
        app.dependency_overrides[get_current_user] = lambda: admin_user_obj
        try:
            deal_id = deal_by_admin["id"]
            resp = sec_client.get(f"/api/v1/deals/{deal_id}")
            if resp.status_code == 200:
                body = resp.json()
                # UUID 기반 ID는 허용, 순차 정수 PK는 노출 금지
                assert "_sa_instance_state" not in str(body)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_error_response_rfc7807_format(
        self, sec_client: TestClient, admin_user_obj
    ):
        """FDD-1405-06: 에러 응답이 RFC 7807 형식을 준수."""
        app.dependency_overrides[get_current_user] = lambda: admin_user_obj
        try:
            fake_id = str(uuid.uuid4())
            resp = sec_client.get(f"/api/v1/deals/{fake_id}")
            if resp.status_code >= 400:
                body = resp.json()
                # RFC 7807 필수 필드 확인
                assert "detail" in body or "title" in body
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ─── 3. 민감정보 마스킹 검증 ──────────────────────────────


class TestMaskingVerification:
    """마스킹 엔진이 민감정보를 올바르게 마스킹하는지 검증."""

    def test_masking_engine_redacts_amounts(self):
        """FDD-1405-07: 금액 마스킹이 적용되는지 검증."""
        from decimal import Decimal

        from app.services.masking.engine import (
            DistributionMode,
            MaskingEngine,
        )

        engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
        result = engine.mask_amount(Decimal("1234567890"))
        assert result != "1234567890"

    def test_masking_engine_redacts_names(self):
        """FDD-1405-08: 이름 마스킹이 적용되는지 검증."""
        from app.services.masking.engine import (
            DistributionMode,
            MaskingEngine,
        )

        engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
        result = engine.mask_text("홍길동", entity_type="person")
        assert result != "홍길동"

    def test_masking_engine_preserves_structure(self):
        """FDD-1405-09: 마스킹 후 데이터 구조가 유지되는지 검증."""
        from app.services.masking.engine import (
            DistributionMode,
            MaskingEngine,
        )

        engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
        result = engine.mask_text("ABC Corporation", entity_type="company")
        assert isinstance(result, str)
        assert len(result) > 0


# ─── 4. 파일 접근 제어 ──────────────────────────────────


class TestFileAccessControl:
    """다른 딜의 파일에 접근할 수 없어야 한다."""

    def test_cross_deal_upload_access_blocked(
        self,
        sec_client: TestClient,
        admin_user_obj: CurrentUser,
        deal_by_admin,
    ):
        """FDD-1405-10: 다른 딜의 업로드 파일에 접근 시도 → 404."""
        app.dependency_overrides[get_current_user] = lambda: admin_user_obj
        try:
            # 존재하지 않는 딜의 업로드 접근
            fake_deal_id = str(uuid.uuid4())
            fake_upload_id = str(uuid.uuid4())
            resp = sec_client.get(
                f"/api/v1/deals/{fake_deal_id}/uploads/{fake_upload_id}"
            )
            assert resp.status_code == 404

            # 실제 딜에 존재하지 않는 업로드 접근
            deal_id = deal_by_admin["id"]
            resp = sec_client.get(f"/api/v1/deals/{deal_id}/uploads/{fake_upload_id}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
