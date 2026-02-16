"""통합 검색 서비스 테스트

ElasticSearch가 없는 환경에서도 안전하게 동작하는지 검증한다.
ES 클라이언트가 None일 때 빈 결과 / 0 / 빈 dict를 반환해야 한다.
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.schemas.search import (
    IndexStatusResponse,
    ReindexResponse,
    SearchQuery,
    SearchResponse,
    SearchResultItem,
)
from app.services.search_service import SearchService

# --- SearchService: ES 클라이언트 None일 때 graceful fallback ---


class TestSearchServiceWithoutES:
    """ES 클라이언트가 없는 환경에서 SearchService 동작 테스트"""

    @pytest.fixture
    def service(self) -> SearchService:
        return SearchService()

    @patch("app.services.search_service.get_es_client", return_value=None)
    async def test_search_returns_empty_when_es_not_available(self, mock_es, service: SearchService):
        """ES 클라이언트 None일 때 빈 결과를 반환한다."""
        items, total = await service.search(q="테스트", type=None, page=1, size=20)
        assert items == []
        assert total == 0

    @patch("app.services.search_service.get_es_client", return_value=None)
    async def test_search_with_type_returns_empty_when_es_not_available(self, mock_es, service: SearchService):
        """ES 클라이언트 None + type 지정 시에도 빈 결과를 반환한다."""
        items, total = await service.search(q="한국투자", type="companies", page=1, size=10)
        assert items == []
        assert total == 0

    @patch("app.services.search_service.get_es_client", return_value=None)
    async def test_reindex_returns_zeros_when_es_not_available(self, mock_es, service: SearchService):
        """ES 클라이언트 None일 때 리인덱싱은 모두 0을 반환한다."""
        # db 세션은 ES가 없으면 사용되지 않으므로 None으로 전달
        counts = await service.reindex_all(db=None)  # type: ignore[arg-type]
        assert counts == {"companies": 0, "funds": 0, "news": 0, "deals": 0}

    @patch("app.services.search_service.get_es_client", return_value=None)
    async def test_get_index_status_returns_empty_when_es_not_available(self, mock_es, service: SearchService):
        """ES 클라이언트 None일 때 인덱스 상태는 빈 dict를 반환한다."""
        status = await service.get_index_status()
        assert status == {}


# --- Pydantic 스키마 유효성 테스트 ---


class TestSearchSchemas:
    """검색 관련 Pydantic 스키마 유효성 테스트"""

    def test_search_query_valid(self):
        """유효한 SearchQuery 생성"""
        query = SearchQuery(q="한국투자파트너스")
        assert query.q == "한국투자파트너스"
        assert query.type is None
        assert query.page == 1
        assert query.size == 20

    def test_search_query_with_all_params(self):
        """모든 파라미터를 지정한 SearchQuery 생성"""
        query = SearchQuery(q="바이오", type="companies", page=3, size=50)
        assert query.q == "바이오"
        assert query.type == "companies"
        assert query.page == 3
        assert query.size == 50

    def test_search_query_empty_q_raises_error(self):
        """빈 검색어는 ValidationError를 발생시킨다."""
        with pytest.raises(ValidationError):
            SearchQuery(q="")

    def test_search_query_too_long_q_raises_error(self):
        """200자를 초과하는 검색어는 ValidationError를 발생시킨다."""
        with pytest.raises(ValidationError):
            SearchQuery(q="a" * 201)

    def test_search_query_page_below_1_raises_error(self):
        """page < 1이면 ValidationError를 발생시킨다."""
        with pytest.raises(ValidationError):
            SearchQuery(q="test", page=0)

    def test_search_query_size_above_100_raises_error(self):
        """size > 100이면 ValidationError를 발생시킨다."""
        with pytest.raises(ValidationError):
            SearchQuery(q="test", size=101)

    def test_search_query_size_below_1_raises_error(self):
        """size < 1이면 ValidationError를 발생시킨다."""
        with pytest.raises(ValidationError):
            SearchQuery(q="test", size=0)

    def test_search_result_item_valid(self):
        """유효한 SearchResultItem 생성"""
        item = SearchResultItem(
            index="kiis_companies",
            id="1",
            score=1.5,
            source={"corp_name": "테스트기업"},
        )
        assert item.index == "kiis_companies"
        assert item.id == "1"
        assert item.score == 1.5
        assert item.source == {"corp_name": "테스트기업"}

    def test_search_response_valid(self):
        """유효한 SearchResponse 생성"""
        response = SearchResponse(
            total=1,
            page=1,
            size=20,
            query="테스트",
            items=[
                SearchResultItem(
                    index="kiis_companies",
                    id="1",
                    score=1.5,
                    source={"corp_name": "테스트기업"},
                ),
            ],
        )
        assert response.total == 1
        assert len(response.items) == 1
        assert response.query == "테스트"

    def test_search_response_empty_items(self):
        """빈 검색 결과 SearchResponse 생성"""
        response = SearchResponse(
            total=0,
            page=1,
            size=20,
            query="없는검색어",
            items=[],
        )
        assert response.total == 0
        assert response.items == []

    def test_reindex_response_valid(self):
        """유효한 ReindexResponse 생성"""
        response = ReindexResponse(
            companies=100,
            funds=50,
            news=200,
            deals=30,
        )
        assert response.companies == 100
        assert response.funds == 50
        assert response.news == 200
        assert response.deals == 30
        assert response.message == "리인덱싱 완료"

    def test_reindex_response_custom_message(self):
        """커스텀 메시지를 가진 ReindexResponse 생성"""
        response = ReindexResponse(
            companies=0,
            funds=0,
            news=0,
            deals=0,
            message="ES 미연결로 리인덱싱 건너뜀",
        )
        assert response.message == "ES 미연결로 리인덱싱 건너뜀"

    def test_index_status_response_valid(self):
        """유효한 IndexStatusResponse 생성"""
        response = IndexStatusResponse(
            indices={
                "kiis_companies": {"docs_count": 100, "size_bytes": 51200},
                "kiis_funds": {"docs_count": 50, "size_bytes": 25600},
                "kiis_news": {"docs_count": 200, "size_bytes": 102400},
                "kiis_deals": {"docs_count": 30, "size_bytes": 15360},
            }
        )
        assert len(response.indices) == 4
        assert response.indices["kiis_companies"]["docs_count"] == 100

    def test_index_status_response_empty(self):
        """빈 인덱스 상태 IndexStatusResponse 생성"""
        response = IndexStatusResponse(indices={})
        assert response.indices == {}
