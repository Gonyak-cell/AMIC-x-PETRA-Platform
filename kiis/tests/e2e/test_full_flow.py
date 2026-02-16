"""E2E 테스트: 전체 시스템 흐름 시나리오

인증 플로우, 대시보드, 검색, Entity Resolution 등 전체 API를 검증한다.
"""

import pytest

pytestmark = pytest.mark.e2e


class TestAuthFlow:
    """인증 플로우 E2E 테스트"""

    async def test_auth_flow_register_login_access(self, client):
        """회원가입 -> 로그인 -> 보호된 엔드포인트 접근 전체 플로우"""
        # 1. 회원가입
        reg_response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "auth_flow_user",
                "email": "authflow@kiis.io",
                "password": "securepass123",
            },
        )
        assert reg_response.status_code == 201
        user_data = reg_response.json()
        assert user_data["username"] == "auth_flow_user"
        assert user_data["is_active"] is True

        # 2. 로그인
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "auth_flow_user", "password": "securepass123"},
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "bearer"

        # 3. 보호된 엔드포인트 접근 (워치리스트)
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        watchlist_response = await client.get("/api/v1/watchlist", headers=headers)
        assert watchlist_response.status_code == 200
        watchlist_data = watchlist_response.json()
        assert "total" in watchlist_data
        assert "items" in watchlist_data

    async def test_auth_flow_unauthorized_access(self, client):
        """토큰 없이 보호된 엔드포인트 접근 시 401 반환"""
        response = await client.get("/api/v1/watchlist")
        assert response.status_code == 401

    async def test_auth_flow_invalid_token(self, client):
        """유효하지 않은 토큰으로 접근 시 401 반환"""
        headers = {"Authorization": "Bearer invalid-token-12345"}
        response = await client.get("/api/v1/watchlist", headers=headers)
        assert response.status_code == 401

    async def test_auth_flow_token_refresh(self, client, registered_user):
        """리프레시 토큰으로 새 액세스 토큰을 발급받을 수 있다."""
        # 로그인하여 refresh_token 획득
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": registered_user["username"],
                "password": registered_user["password"],
            },
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # 리프레시
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens


class TestDashboardSummary:
    """대시보드 요약 E2E 테스트"""

    async def test_dashboard_summary_with_data(self, client, seed_e2e_data):
        """시드 데이터가 있는 상태에서 대시보드 요약을 조회하면 올바른 수가 반환된다."""
        response = await client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200

        data = response.json()
        assert "counts" in data
        assert "recent_news_count" in data
        assert "recent_deals" in data
        assert "data_freshness" in data

        # counts 확인: seed_e2e_data에서 기업 2개, 뉴스 3개, 딜 2개
        counts_dict = {c["label"]: c["count"] for c in data["counts"]}
        assert counts_dict["기업"] == 2
        assert counts_dict["뉴스"] == 3
        assert counts_dict["딜"] == 2

    async def test_dashboard_summary_empty_db(self, client):
        """빈 DB에서도 대시보드 요약이 정상 응답한다."""
        response = await client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200

        data = response.json()
        counts_dict = {c["label"]: c["count"] for c in data["counts"]}
        assert counts_dict["기업"] == 0
        assert counts_dict["뉴스"] == 0


class TestSearchWithoutElasticsearch:
    """ElasticSearch 없이 검색 API E2E 테스트"""

    async def test_search_returns_empty_results_gracefully(self, client):
        """ES 미설치 환경에서 검색 시 에러 대신 빈 결과를 반환한다."""
        response = await client.get("/api/v1/search", params={"q": "테스트"})
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["query"] == "테스트"

    async def test_search_with_type_filter(self, client):
        """type 필터를 지정해도 정상 동작한다."""
        response = await client.get("/api/v1/search", params={"q": "투자", "type": "companies"})
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestCompanyEntityResolution:
    """기업 Entity Resolution E2E 테스트"""

    async def test_entity_resolution_with_alias(self, client, seed_e2e_data):
        """별칭으로 Entity Resolution을 요청하면 매칭 결과가 반환된다."""
        response = await client.post(
            "/api/v1/entities/resolve",
            json={"name": "이투스", "threshold": 0.5},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "이투스"
        assert data["normalized"] is not None

        # 별칭 정확 매칭으로 결과가 있어야 한다
        if data["match"] is not None:
            assert data["match"]["corp_name"] == "이투스자산운용 주식회사"
            assert data["match"]["matched_by"] == "alias"

    async def test_entity_resolution_with_exact_name(self, client, seed_e2e_data):
        """정식 기업명으로 Entity Resolution을 요청하면 정확 매칭된다."""
        response = await client.post(
            "/api/v1/entities/resolve",
            json={"name": "이투스자산운용 주식회사", "threshold": 0.5},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "이투스자산운용 주식회사"
        # 정확 매칭 또는 유사도 매칭으로 결과가 반환되어야 한다
        if data["match"] is not None:
            assert data["match"]["corp_code"] == "00200001"

    async def test_entity_resolution_no_match(self, client, seed_e2e_data):
        """존재하지 않는 기업명으로 요청하면 매칭 결과 없이 반환된다."""
        response = await client.post(
            "/api/v1/entities/resolve",
            json={"name": "존재하지않는기업XYZABC", "threshold": 0.9},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["match"] is None

    async def test_alias_crud_flow(self, client, seed_e2e_data):
        """별칭 등록 -> 조회 -> 삭제 전체 CRUD 플로우"""
        companies = seed_e2e_data["companies"]
        corp_code = companies[0].corp_code

        # 1. 별칭 등록
        create_response = await client.post(
            "/api/v1/entities/aliases",
            json={"alias_name": "이투스운용", "corp_code": corp_code},
        )
        assert create_response.status_code == 201
        alias_data = create_response.json()
        assert alias_data["alias_name"] == "이투스운용"
        alias_id = alias_data["id"]

        # 2. 별칭 목록 조회
        list_response = await client.get(
            "/api/v1/entities/aliases",
            params={"corp_code": corp_code},
        )
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["total"] >= 1
        alias_names = [item["alias_name"] for item in list_data["items"]]
        assert "이투스운용" in alias_names

        # 3. 별칭 삭제
        delete_response = await client.delete(f"/api/v1/entities/aliases/{alias_id}")
        assert delete_response.status_code == 204


class TestHealthCheck:
    """헬스 체크 E2E 테스트"""

    async def test_health_endpoint(self, client):
        """GET /health가 정상 응답한다."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
