"""Diagrams 라우트 테스트.

다이어그램 CRUD + PNG 내보내기 엔드포인트 검증.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import create_app
from src.api.db.models.diagram import Diagram
from src.api.db.models.document import Document
from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user


# ── Test helpers ─────────────────────────────────────────────

_NOW = datetime.now(timezone.utc)

_SAMPLE_EXCALIDRAW: dict = {
    "type": "excalidraw",
    "version": 2,
    "elements": [{"id": "el1", "type": "rectangle"}],
    "appState": {},
}

# Minimal valid PNG — magic 8 bytes + padding
_VALID_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _make_user(role: str = "USER") -> MagicMock:
    """테스트 User mock."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    user.email = "test@example.com"
    return user


def _make_document(owner_id: uuid.UUID) -> MagicMock:
    """테스트 Document mock."""
    doc = MagicMock(spec=Document)
    doc.id = uuid.uuid4()
    doc.owner_id = owner_id
    doc.created_at = _NOW
    doc.updated_at = _NOW
    return doc


def _make_diagram(document_id: uuid.UUID, **kwargs: object) -> MagicMock:
    """테스트 Diagram mock."""
    diagram = MagicMock(spec=Diagram)
    diagram.id = kwargs.get("id", uuid.uuid4())
    diagram.document_id = document_id
    diagram.diagram_type = kwargs.get("diagram_type", "shareholding")
    diagram.title = kwargs.get("title", "주주관계도")
    diagram.excalidraw_data = kwargs.get("excalidraw_data", _SAMPLE_EXCALIDRAW)
    diagram.png_path = kwargs.get("png_path")
    diagram.created_at = _NOW
    diagram.updated_at = _NOW
    return diagram


def _scalar_result(value: object) -> MagicMock:
    """scalar_one_or_none() 를 반환하는 mock execute result."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_result(values: list[object]) -> MagicMock:
    """scalars().all() 을 반환하는 mock execute result."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def test_user() -> MagicMock:
    return _make_user()


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()  # session.add() 는 동기 메서드
    return session


@pytest.fixture
def route_app(test_user: MagicMock, mock_session: AsyncMock):  # type: ignore[type-arg]
    """라우트 테스트용 앱 (인증 우회 + 세션 모킹)."""
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_async_session] = lambda: mock_session
    return app


@pytest.fixture
async def route_client(route_app) -> AsyncClient:  # type: ignore[type-arg]
    async with AsyncClient(
        transport=ASGITransport(app=route_app),
        base_url="http://test",
    ) as client:
        yield client


# ── GET /documents/{id}/diagrams ─────────────────────────────


class TestListDiagrams:
    """GET /api/v1/documents/{id}/diagrams 테스트."""

    @pytest.mark.asyncio
    async def test_list_returns_200(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """정상 목록 조회 시 200."""
        doc = _make_document(owner_id=test_user.id)
        diagram = _make_diagram(document_id=doc.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalars_result([diagram]),
            ]
        )

        resp = await route_client.get(f"/api/v1/documents/{doc.id}/diagrams")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["diagram_type"] == "shareholding"
        assert data[0]["title"] == "주주관계도"
        # DiagramListResponse 에는 excalidraw_data 없음
        assert "excalidraw_data" not in data[0]

    @pytest.mark.asyncio
    async def test_list_empty_returns_200(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """다이어그램 없는 문서 조회 시 빈 배열 200."""
        doc = _make_document(owner_id=test_user.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalars_result([]),
            ]
        )

        resp = await route_client.get(f"/api/v1/documents/{doc.id}/diagrams")

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_document_not_found_returns_404(
        self,
        route_client: AsyncClient,
        mock_session: AsyncMock,
    ) -> None:
        """존재하지 않는 문서 ID 시 404."""
        mock_session.execute = AsyncMock(return_value=_scalar_result(None))

        resp = await route_client.get(f"/api/v1/documents/{uuid.uuid4()}/diagrams")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_forbidden_returns_403(
        self,
        route_client: AsyncClient,
        mock_session: AsyncMock,
    ) -> None:
        """타 사용자 문서 접근 시 403."""
        doc = _make_document(owner_id=uuid.uuid4())

        mock_session.execute = AsyncMock(return_value=_scalar_result(doc))

        resp = await route_client.get(f"/api/v1/documents/{doc.id}/diagrams")

        assert resp.status_code == 403


# ── POST /documents/{id}/diagrams ────────────────────────────


class TestCreateDiagram:
    """POST /api/v1/documents/{id}/diagrams 테스트."""

    @pytest.mark.asyncio
    async def test_create_returns_201(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """정상 생성 시 201."""
        doc = _make_document(owner_id=test_user.id)

        mock_session.execute = AsyncMock(return_value=_scalar_result(doc))

        async def _fake_refresh(obj: object) -> None:
            obj.created_at = _NOW  # type: ignore[attr-defined]
            obj.updated_at = _NOW  # type: ignore[attr-defined]

        mock_session.refresh = AsyncMock(side_effect=_fake_refresh)

        resp = await route_client.post(
            f"/api/v1/documents/{doc.id}/diagrams",
            json={
                "diagram_type": "shareholding",
                "title": "주주관계도",
                "excalidraw_data": _SAMPLE_EXCALIDRAW,
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["diagram_type"] == "shareholding"
        assert data["title"] == "주주관계도"
        assert data["excalidraw_data"] is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_invalid_type_returns_422(
        self,
        route_client: AsyncClient,
    ) -> None:
        """유효하지 않은 diagram_type 시 422."""
        resp = await route_client.post(
            f"/api/v1/documents/{uuid.uuid4()}/diagrams",
            json={
                "diagram_type": "invalid_type",
                "title": "테스트",
                "excalidraw_data": _SAMPLE_EXCALIDRAW,
            },
        )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_oversized_excalidraw_data_returns_422(
        self,
        route_client: AsyncClient,
    ) -> None:
        """excalidraw_data가 5MB 초과 시 422."""
        with patch(
            "src.api.schemas.diagrams._MAX_EXCALIDRAW_DATA_BYTES",
            100,
        ):
            big_data = {
                "type": "excalidraw",
                "version": 2,
                "elements": [{"x": "A" * 200}],
                "appState": {},
            }
            resp = await route_client.post(
                f"/api/v1/documents/{uuid.uuid4()}/diagrams",
                json={
                    "diagram_type": "shareholding",
                    "title": "테스트",
                    "excalidraw_data": big_data,
                },
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_document_not_found_returns_404(
        self,
        route_client: AsyncClient,
        mock_session: AsyncMock,
    ) -> None:
        """존재하지 않는 문서에 생성 시 404."""
        mock_session.execute = AsyncMock(return_value=_scalar_result(None))

        resp = await route_client.post(
            f"/api/v1/documents/{uuid.uuid4()}/diagrams",
            json={
                "diagram_type": "org_chart",
                "title": "조직도",
                "excalidraw_data": _SAMPLE_EXCALIDRAW,
            },
        )

        assert resp.status_code == 404


# ── GET /documents/{id}/diagrams/{diagram_id} ────────────────


class TestGetDiagram:
    """GET /api/v1/documents/{id}/diagrams/{diagram_id} 테스트."""

    @pytest.mark.asyncio
    async def test_get_returns_200_with_excalidraw_data(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """상세 조회 시 excalidraw_data 포함 200."""
        doc = _make_document(owner_id=test_user.id)
        diagram = _make_diagram(document_id=doc.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalar_result(diagram),
            ]
        )

        resp = await route_client.get(
            f"/api/v1/documents/{doc.id}/diagrams/{diagram.id}"
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["excalidraw_data"] is not None
        assert data["diagram_type"] == "shareholding"

    @pytest.mark.asyncio
    async def test_get_diagram_not_found_returns_404(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """존재하지 않는 다이어그램 조회 시 404."""
        doc = _make_document(owner_id=test_user.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalar_result(None),
            ]
        )

        resp = await route_client.get(
            f"/api/v1/documents/{doc.id}/diagrams/{uuid.uuid4()}"
        )

        assert resp.status_code == 404


# ── PUT /documents/{id}/diagrams/{diagram_id} ────────────────


class TestUpdateDiagram:
    """PUT /api/v1/documents/{id}/diagrams/{diagram_id} 테스트."""

    @pytest.mark.asyncio
    async def test_update_returns_200(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """수정 시 200."""
        doc = _make_document(owner_id=test_user.id)
        diagram = _make_diagram(document_id=doc.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalar_result(diagram),
            ]
        )

        updated_data = {
            **_SAMPLE_EXCALIDRAW,
            "elements": [{"id": "el2", "type": "ellipse"}],
        }

        resp = await route_client.put(
            f"/api/v1/documents/{doc.id}/diagrams/{diagram.id}",
            json={"excalidraw_data": updated_data},
        )

        assert resp.status_code == 200
        assert diagram.excalidraw_data == updated_data
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_update_oversized_excalidraw_data_returns_422(
        self,
        route_client: AsyncClient,
    ) -> None:
        """수정 시 excalidraw_data가 5MB 초과하면 422."""
        with patch(
            "src.api.schemas.diagrams._MAX_EXCALIDRAW_DATA_BYTES",
            100,
        ):
            big_data = {
                "type": "excalidraw",
                "version": 2,
                "elements": [{"x": "A" * 200}],
                "appState": {},
            }
            resp = await route_client.put(
                f"/api/v1/documents/{uuid.uuid4()}/diagrams/{uuid.uuid4()}",
                json={"excalidraw_data": big_data},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_diagram_not_found_returns_404(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """존재하지 않는 다이어그램 수정 시 404."""
        doc = _make_document(owner_id=test_user.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalar_result(None),
            ]
        )

        resp = await route_client.put(
            f"/api/v1/documents/{doc.id}/diagrams/{uuid.uuid4()}",
            json={"excalidraw_data": _SAMPLE_EXCALIDRAW},
        )

        assert resp.status_code == 404


# ── DELETE /documents/{id}/diagrams/{diagram_id} ─────────────


class TestDeleteDiagram:
    """DELETE /api/v1/documents/{id}/diagrams/{diagram_id} 테스트."""

    @pytest.mark.asyncio
    async def test_delete_returns_204(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """삭제 시 204."""
        doc = _make_document(owner_id=test_user.id)
        diagram = _make_diagram(document_id=doc.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalar_result(diagram),
            ]
        )

        resp = await route_client.delete(
            f"/api/v1/documents/{doc.id}/diagrams/{diagram.id}"
        )

        assert resp.status_code == 204
        mock_session.delete.assert_awaited_once_with(diagram)
        mock_session.commit.assert_awaited()


# ── POST .../export-png ──────────────────────────────────────


class TestExportPng:
    """POST .../export-png 테스트."""

    @pytest.mark.asyncio
    async def test_export_valid_png_returns_200(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
        tmp_path,
    ) -> None:
        """유효한 PNG 내보내기 시 200."""
        doc = _make_document(owner_id=test_user.id)
        diagram = _make_diagram(document_id=doc.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalar_result(diagram),
            ]
        )

        mock_config = MagicMock()
        mock_config.output_dir = str(tmp_path)

        with patch(
            "src.api.routes.diagrams.get_config",
            return_value=mock_config,
        ):
            resp = await route_client.post(
                f"/api/v1/documents/{doc.id}/diagrams/{diagram.id}/export-png",
                files={"file": ("diagram.png", _VALID_PNG, "image/png")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "png_path" in data
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_export_oversized_png_returns_413(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """크기 제한 초과 PNG 시 413."""
        doc = _make_document(owner_id=test_user.id)
        diagram = _make_diagram(document_id=doc.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalar_result(diagram),
            ]
        )

        # _MAX_PNG_SIZE 를 50바이트로 패치하여 빠른 테스트
        with patch("src.api.routes.diagrams._MAX_PNG_SIZE", 50):
            oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
            resp = await route_client.post(
                f"/api/v1/documents/{doc.id}/diagrams/{diagram.id}/export-png",
                files={"file": ("large.png", oversized, "image/png")},
            )

        assert resp.status_code == 413

    @pytest.mark.asyncio
    async def test_export_invalid_magic_returns_422(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """PNG 매직 바이트 불일치 시 422."""
        doc = _make_document(owner_id=test_user.id)
        diagram = _make_diagram(document_id=doc.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalar_result(diagram),
            ]
        )

        not_png = b"NOT_A_PNG_FILE_CONTENT"

        resp = await route_client.post(
            f"/api/v1/documents/{doc.id}/diagrams/{diagram.id}/export-png",
            files={"file": ("fake.png", not_png, "image/png")},
        )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_export_png_write_ioerror_returns_500(
        self,
        route_client: AsyncClient,
        test_user: MagicMock,
        mock_session: AsyncMock,
        tmp_path,
    ) -> None:
        """PNG 파일 쓰기 중 IOError 발생 시 500."""
        doc = _make_document(owner_id=test_user.id)
        diagram = _make_diagram(document_id=doc.id)

        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_result(doc),
                _scalar_result(diagram),
            ]
        )

        mock_config = MagicMock()
        mock_config.output_dir = str(tmp_path)

        with (
            patch(
                "src.api.routes.diagrams.get_config",
                return_value=mock_config,
            ),
            patch(
                "pathlib.Path.write_bytes",
                side_effect=OSError("disk full"),
            ),
        ):
            resp = await route_client.post(
                f"/api/v1/documents/{doc.id}/diagrams/{diagram.id}/export-png",
                files={"file": ("diagram.png", _VALID_PNG, "image/png")},
            )

        assert resp.status_code == 500
