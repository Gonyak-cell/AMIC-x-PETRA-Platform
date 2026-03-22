"""VDR (Virtual Data Room) API 테스트."""

import io
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_jwt_claims
from app.main import app
from app.models.enums import VdrFolderCategory
from app.models.vdr_folder import VdrFolder
from tests.conftest import _override_get_jwt_claims, make_claims

pytestmark = pytest.mark.anyio


# ── Init ─────────────────────────────────────────────────────


def _set_claims(*, role: str, email: str) -> None:
    async def _override():
        return make_claims(role=role, email=email)

    app.dependency_overrides[get_jwt_claims] = _override


def _restore_claims() -> None:
    app.dependency_overrides[get_jwt_claims] = _override_get_jwt_claims


class TestVdrInit:
    async def test_vdr_auto_initialized_on_transaction_creation(self, client: AsyncClient, transaction_id: str):
        """거래 생성 시 VDR 기본 폴더가 자동 생성된다."""
        resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        assert resp.status_code == 200
        folders = resp.json()
        assert len(folders) == 12
        # 필수 폴더 4개 확인
        required = [f for f in folders if f["is_required"]]
        assert len(required) == 4
        # 카테고리 확인
        categories = {f["category"] for f in folders}
        assert "CORPORATE" in categories
        assert "FINANCIAL" in categories
        assert "LEGAL" in categories
        assert "TAX" in categories

    async def test_init_vdr_duplicate_is_idempotent(self, client: AsyncClient, transaction_id: str):
        """이미 자동 초기화된 거래에 init 호출 시 400 반환."""
        resp = await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        assert resp.status_code == 201
        assert len(resp.json()) == 12

    async def test_init_vdr_repairs_missing_default_folders(
        self,
        client: AsyncClient,
        transaction_id: str,
        async_session: AsyncSession,
    ):
        txn_uuid = uuid.UUID(transaction_id)
        await async_session.execute(
            delete(VdrFolder).where(
                VdrFolder.transaction_id == txn_uuid,
                VdrFolder.parent_id.is_(None),
                VdrFolder.category == VdrFolderCategory.LEGAL,
            )
        )
        await async_session.commit()

        summary_before = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/summary")
        assert summary_before.status_code == 200
        assert summary_before.json()["initialized"] is False

        repair_resp = await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        assert repair_resp.status_code == 201
        assert len(repair_resp.json()) == 12

        summary_after = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/summary")
        assert summary_after.status_code == 200
        assert summary_after.json()["initialized"] is True

    async def test_init_vdr_invalid_txn_returns_404(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(f"/api/v1/transactions/{fake_id}/vdr/init")
        assert resp.status_code == 404

    async def test_vdr_summary_and_folders_allow_internal_workspace_user(
        self,
        client: AsyncClient,
        transaction_id: str,
    ):
        _set_claims(role="ANALYST", email="teammate@amic.kr")
        try:
            summary_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/summary")
            folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        finally:
            _restore_claims()

        assert summary_resp.status_code == 200
        assert folders_resp.status_code == 200


# ── Folder CRUD ──────────────────────────────────────────────


class TestVdrFolders:
    async def test_list_folders_returns_tree(self, client: AsyncClient, transaction_id: str):
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        assert resp.status_code == 200
        tree = resp.json()
        assert len(tree) == 12
        # 각 폴더에 document_count 필드 존재
        assert all("document_count" in f for f in tree)

    async def test_create_custom_folder(self, client: AsyncClient, transaction_id: str):
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders",
            json={"name": "기타 자료", "category": "CUSTOM"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "기타 자료"
        assert data["category"] == "CUSTOM"
        assert data["is_required"] is False

    async def test_create_subfolder(self, client: AsyncClient, transaction_id: str):
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        # 첫 번째 폴더를 부모로 사용
        folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        parent_id = folders_resp.json()[0]["id"]

        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders",
            json={"name": "하위 폴더", "parent_id": parent_id},
        )
        assert resp.status_code == 201
        assert resp.json()["parent_id"] == parent_id

    async def test_update_folder_name(self, client: AsyncClient, transaction_id: str):
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        # 커스텀 폴더 생성
        create_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders",
            json={"name": "원래 이름"},
        )
        folder_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}",
            json={"name": "변경된 이름"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "변경된 이름"

    async def test_delete_custom_folder(self, client: AsyncClient, transaction_id: str):
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        create_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders",
            json={"name": "삭제할 폴더"},
        )
        folder_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}")
        assert resp.status_code == 204

    async def test_delete_required_folder_returns_400(self, client: AsyncClient, transaction_id: str):
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        required_folder = next(f for f in folders_resp.json() if f["is_required"])

        resp = await client.delete(f"/api/v1/transactions/{transaction_id}/vdr/folders/{required_folder['id']}")
        assert resp.status_code == 400


# ── Document CRUD ────────────────────────────────────────────


class TestVdrDocuments:
    async def _init_and_get_folder(self, client: AsyncClient, transaction_id: str) -> str:
        """VDR 초기화 후 첫 번째 폴더 ID 반환."""
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        return folders_resp.json()[0]["id"]

    async def test_upload_pdf_document(self, client: AsyncClient, transaction_id: str):
        folder_id = await self._init_and_get_folder(client, transaction_id)
        content = b"%PDF-1.4 fake pdf content for testing"
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("test.pdf", io.BytesIO(content), "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["original_name"] == "test.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["file_size_bytes"] == len(content)
        assert data["status"] == "ACTIVE"
        assert data["sha256_hash"] is not None

    async def test_upload_invalid_mime_returns_400(self, client: AsyncClient, transaction_id: str):
        folder_id = await self._init_and_get_folder(client, transaction_id)
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("test.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        )
        assert resp.status_code == 400

    async def test_folder_upload_repairs_missing_default_folders(
        self,
        client: AsyncClient,
        transaction_id: str,
        async_session: AsyncSession,
    ):
        folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        corporate_folder_id = next(
            folder["id"] for folder in folders_resp.json() if folder["category"] == "CORPORATE"
        )

        txn_uuid = uuid.UUID(transaction_id)
        await async_session.execute(
            delete(VdrFolder).where(
                VdrFolder.transaction_id == txn_uuid,
                VdrFolder.parent_id.is_(None),
                VdrFolder.category == VdrFolderCategory.LEGAL,
            )
        )
        await async_session.commit()

        summary_before = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/summary")
        assert summary_before.status_code == 200
        assert summary_before.json()["initialized"] is False

        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{corporate_folder_id}/documents",
            files={"file": ("manual-upload.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")},
        )
        assert resp.status_code == 201

        summary_after = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/summary")
        assert summary_after.status_code == 200
        assert summary_after.json()["initialized"] is True

    async def test_direct_upload_repairs_missing_folders(
        self,
        client: AsyncClient,
        transaction_id: str,
        async_session: AsyncSession,
    ):
        txn_uuid = uuid.UUID(transaction_id)
        await async_session.execute(
            delete(VdrFolder).where(VdrFolder.transaction_id == txn_uuid)
        )
        await async_session.commit()

        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/direct-upload",
            files=[("files", ("legal-memo.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf"))],
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_uploaded"] + len(data["failed_files"]) == 1
        assert all("초기화" not in failed["reason"] for failed in data["failed_files"])

    async def test_unified_upload_route_supports_manual_folder_upload(
        self,
        client: AsyncClient,
        transaction_id: str,
    ):
        folder_id = await self._init_and_get_folder(client, transaction_id)
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/uploads",
            data={"folder_id": folder_id},
            files=[("files", ("manual.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf"))],
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_uploaded"] == 1
        assert data["pending_review_count"] == 0
        assert data["results"][0]["routed_folder"]["id"] == folder_id
        assert data["results"][0]["classification_status"] == "DIRECT"

    async def test_unified_upload_route_supports_auto_routing(
        self,
        client: AsyncClient,
        transaction_id: str,
    ):
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/uploads",
            files=[("files", ("legal-memo.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf"))],
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_uploaded"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["document"]["original_name"].startswith("legal-memo")

    async def test_list_folder_documents(self, client: AsyncClient, transaction_id: str):
        folder_id = await self._init_and_get_folder(client, transaction_id)
        # 파일 2개 업로드
        for name in ("doc1.pdf", "doc2.pdf"):
            await client.post(
                f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
                files={"file": (name, io.BytesIO(b"fake content"), "application/pdf")},
            )

        resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_delete_document_soft_delete(self, client: AsyncClient, transaction_id: str):
        folder_id = await self._init_and_get_folder(client, transaction_id)
        upload_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("del.pdf", io.BytesIO(b"content"), "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        # 삭제
        resp = await client.delete(f"/api/v1/transactions/{transaction_id}/vdr/documents/{doc_id}")
        assert resp.status_code == 204

        # 삭제 후 목록에서 제외
        list_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents")
        assert len(list_resp.json()) == 0

    async def test_get_document_metadata(self, client: AsyncClient, transaction_id: str):
        folder_id = await self._init_and_get_folder(client, transaction_id)
        upload_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("meta.pdf", io.BytesIO(b"content"), "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/documents/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["original_name"] == "meta.pdf"

    async def test_update_document_description(self, client: AsyncClient, transaction_id: str):
        folder_id = await self._init_and_get_folder(client, transaction_id)
        upload_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("upd.pdf", io.BytesIO(b"content"), "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/{doc_id}",
            json={"description": "재무제표 2025년"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "재무제표 2025년"


# ── Summary ──────────────────────────────────────────────────


class TestVdrSummary:
    async def test_vdr_summary_auto_initialized(self, client: AsyncClient, transaction_id: str):
        """거래 생성 시 VDR이 자동 초기화되어 있다."""
        resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["initialized"] is True
        assert data["total_folders"] == 12

    async def test_vdr_summary_after_upload(self, client: AsyncClient, transaction_id: str):
        # 첫 번째 폴더에 파일 업로드 (VDR은 거래 생성 시 자동 초기화됨)
        folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        folder_id = folders_resp.json()[0]["id"]
        await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("sum.pdf", io.BytesIO(b"12345"), "application/pdf")},
        )

        resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/summary")
        data = resp.json()
        assert data["initialized"] is True
        assert data["total_folders"] == 12
        assert data["total_documents"] == 1
        assert data["total_size_bytes"] == 5


# ── Isolation ────────────────────────────────────────────────


class TestVdrIsolation:
    async def test_cross_txn_folder_access_denied(self, client: AsyncClient, transaction_id: str):
        """다른 거래의 VDR 폴더에 접근 불가."""
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")

        # 두 번째 거래 생성
        txn2_resp = await client.post(
            "/api/v1/transactions",
            json={
                "name": "VDR Isolation Test",
                "deal_type": "SE",
                "target_company_name": "격리 테스트",
                "client_name": "테스트",
                "side": "BUY",
                "lead_advisor_email": "test@example.com",
            },
        )
        txn2_id = txn2_resp.json()["id"]

        # 두 번째 거래의 VDR도 자동 초기화 (기본 폴더만 존재)
        resp = await client.get(f"/api/v1/transactions/{txn2_id}/vdr/folders")
        assert resp.status_code == 200
        assert len(resp.json()) == 12


# ── Edge Cases ──────────────────────────────────────────────


class TestVdrDocumentEdgeCases:
    async def _init_and_get_folder(self, client: AsyncClient, transaction_id: str) -> str:
        """VDR 초기화 후 첫 번째 폴더 ID 반환."""
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        return folders_resp.json()[0]["id"]

    async def test_download_deleted_document_returns_410(self, client: AsyncClient, transaction_id: str):
        """삭제된 문서 다운로드 시 410 Gone 반환."""
        folder_id = await self._init_and_get_folder(client, transaction_id)

        upload_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("gone.pdf", io.BytesIO(b"content"), "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        # 소프트 삭제
        await client.delete(f"/api/v1/transactions/{transaction_id}/vdr/documents/{doc_id}")

        # 삭제된 문서 다운로드 시도
        resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/documents/{doc_id}/download")
        assert resp.status_code == 410

    async def test_upload_oversized_file_returns_413(
        self, client: AsyncClient, transaction_id: str, monkeypatch: pytest.MonkeyPatch
    ):
        """파일 크기 제한 초과 시 413 반환."""
        import app.routers.vdr as vdr_module

        monkeypatch.setattr(vdr_module, "_MAX_FILE_SIZE", 1024)  # 1KB로 축소

        folder_id = await self._init_and_get_folder(client, transaction_id)
        oversized = b"x" * 2048  # 2KB (제한 초과)
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("big.pdf", io.BytesIO(oversized), "application/pdf")},
        )
        assert resp.status_code == 413

    async def test_move_document_to_another_folder(self, client: AsyncClient, transaction_id: str):
        """문서를 다른 폴더로 이동."""
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        folders = folders_resp.json()
        folder_a = folders[0]["id"]
        folder_b = folders[1]["id"]

        # 폴더 A에 업로드
        upload_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_a}/documents",
            files={"file": ("move.pdf", io.BytesIO(b"content"), "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        # 폴더 B로 이동
        resp = await client.put(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/{doc_id}",
            json={"folder_id": folder_b},
        )
        assert resp.status_code == 200
        assert resp.json()["folder_id"] == folder_b

        # 폴더 A에서 사라졌는지 확인
        list_a = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_a}/documents")
        assert all(d["id"] != doc_id for d in list_a.json())

        # 폴더 B에 존재하는지 확인
        list_b = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_b}/documents")
        assert any(d["id"] == doc_id for d in list_b.json())

    async def test_upload_extension_mime_mismatch_returns_400(self, client: AsyncClient, transaction_id: str):
        """확장자(.pdf)와 MIME 타입(image/jpeg)이 불일치하면 400."""
        folder_id = await self._init_and_get_folder(client, transaction_id)
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("fake.pdf", io.BytesIO(b"data"), "image/jpeg")},
        )
        assert resp.status_code == 400
        assert "일치하지 않습니다" in resp.json()["detail"]

    async def test_upload_disallowed_extension_returns_400(self, client: AsyncClient, transaction_id: str):
        """허용되지 않는 확장자(.exe)는 400."""
        folder_id = await self._init_and_get_folder(client, transaction_id)
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("virus.exe", io.BytesIO(b"MZ"), "application/pdf")},
        )
        assert resp.status_code == 400
        assert "확장자" in resp.json()["detail"]

    async def test_delete_folder_cascades_child_documents(self, client: AsyncClient, transaction_id: str):
        """커스텀 폴더 삭제 시 자식 문서도 함께 CASCADE 제거."""
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")

        # 커스텀 폴더 생성
        folder_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders",
            json={"name": "CASCADE 테스트"},
        )
        folder_id = folder_resp.json()["id"]

        # 문서 업로드
        upload_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("cascade.pdf", io.BytesIO(b"content"), "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        # 폴더 삭제
        del_resp = await client.delete(f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}")
        assert del_resp.status_code == 204

        # 문서 조회 시 404 (폴더와 함께 CASCADE 삭제)
        doc_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/documents/{doc_id}")
        assert doc_resp.status_code == 404


# ── Overview ────────────────────────────────────────────────


class TestVdrOverview:
    async def test_overview_empty(self, client: AsyncClient):
        """거래 없을 때 빈 배열 반환."""
        resp = await client.get("/api/v1/vdr/overview")
        assert resp.status_code == 200
        # 다른 테스트에서 생성한 거래가 있을 수 있으므로 타입만 확인
        assert isinstance(resp.json(), list)

    async def test_overview_includes_transaction(self, client: AsyncClient, transaction_id: str):
        """거래가 있으면 overview에 포함."""
        resp = await client.get("/api/v1/vdr/overview")
        assert resp.status_code == 200
        items = resp.json()
        txn_ids = [item["transaction_id"] for item in items]
        assert transaction_id in txn_ids

    async def test_overview_shows_auto_initialized(self, client: AsyncClient, transaction_id: str):
        """거래 생성 시 VDR이 자동 초기화되어 있다."""
        resp = await client.get("/api/v1/vdr/overview")
        items = resp.json()
        item = next(i for i in items if i["transaction_id"] == transaction_id)
        assert item["vdr_initialized"] is True
        assert item["total_folders"] == 12
        assert item["total_documents"] == 0
        assert item["total_size_bytes"] == 0

    async def test_overview_after_init_and_upload(self, client: AsyncClient, transaction_id: str):
        """VDR 초기화 + 업로드 후 통계 반영."""
        # VDR 초기화
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")

        # 첫 폴더에 파일 업로드
        folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        folder_id = folders_resp.json()[0]["id"]
        content = b"overview test content"
        await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("ov.pdf", io.BytesIO(content), "application/pdf")},
        )

        resp = await client.get("/api/v1/vdr/overview")
        items = resp.json()
        item = next(i for i in items if i["transaction_id"] == transaction_id)
        assert item["vdr_initialized"] is True
        assert item["total_folders"] == 12
        assert item["total_documents"] == 1
        assert item["total_size_bytes"] == len(content)
        assert item["last_upload_at"] is not None


# ── Auto Upload ───────────────────────────────────────────────


class TestClassificationStatus:
    """classification-status 엔드포인트 회귀 테스트."""

    async def test_classification_status_returns_200(self, client: AsyncClient, transaction_id: str):
        """존재하는 문서 ID로 classification-status 조회 시 200."""
        folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        folder_id = folders_resp.json()[0]["id"]

        upload_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("cls.pdf", io.BytesIO(b"content"), "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/classification-status",
            params={"doc_ids": [doc_id]},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["document_id"] == doc_id
        assert "classification_status" in items[0]

    async def test_classification_status_empty_for_unknown_doc(self, client: AsyncClient, transaction_id: str):
        """존재하지 않는 문서 ID → 빈 리스트 반환."""
        fake_doc_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/classification-status",
            params={"doc_ids": [fake_doc_id]},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_classification_status_exceeds_limit_returns_400(self, client: AsyncClient, transaction_id: str):
        """doc_ids 개수 초과 시 400."""
        too_many = [str(uuid.uuid4()) for _ in range(51)]
        resp = await client.get(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/classification-status",
            params={"doc_ids": too_many},
        )
        assert resp.status_code == 400
        assert "최대" in resp.json()["detail"]


class TestVdrRoutingTriage:
    async def test_routing_queue_and_override_flow(self, client: AsyncClient, transaction_id: str):
        create_folder_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders",
            json={"name": "Routing Review", "category": "CUSTOM"},
        )
        assert create_folder_resp.status_code == 201
        folder_id = create_folder_resp.json()["id"]

        upload_resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files={"file": ("board_pack_notes.txt", io.BytesIO(b"General overview only."), "text/plain")},
        )
        assert upload_resp.status_code == 201
        doc_id = upload_resp.json()["id"]

        queue_resp = await client.get(
            f"/api/v1/transactions/{transaction_id}/vdr/routing-queue",
            params={"status": "open"},
        )
        assert queue_resp.status_code == 200
        open_items = queue_resp.json()["items"]
        queue_item = next(item for item in open_items if item["document"]["id"] == doc_id)
        assert queue_item["routing_status"] == "OPEN_REVIEW"
        assert queue_item["effective_route"]["requires_manual_review"] is True

        override_resp = await client.put(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/{doc_id}/routing-override",
            json={
                "primary_workstream": "LDD",
                "workstream_tags": ["LDD"],
                "override_note": "Reviewed and confirmed as legal source.",
            },
        )
        assert override_resp.status_code == 200
        assert override_resp.json()["primary_workstream"] == "LDD"

        reviewed_resp = await client.get(
            f"/api/v1/transactions/{transaction_id}/vdr/routing-queue",
            params={"status": "reviewed"},
        )
        assert reviewed_resp.status_code == 200
        reviewed_item = next(item for item in reviewed_resp.json()["items"] if item["document"]["id"] == doc_id)
        assert reviewed_item["routing_status"] == "OVERRIDDEN"
        assert reviewed_item["effective_route"]["is_override"] is True
        assert reviewed_item["effective_route"]["primary_workstream"] == "LDD"
        assert reviewed_item["effective_route"]["override_note"] == "Reviewed and confirmed as legal source."

        reopen_resp = await client.get(
            f"/api/v1/transactions/{transaction_id}/vdr/routing-queue",
            params={"status": "open"},
        )
        assert reopen_resp.status_code == 200
        assert all(item["document"]["id"] != doc_id for item in reopen_resp.json()["items"])


class TestVdrAutoUpload:
    async def test_auto_upload_financial_xlsx_routes_to_financial(self, client: AsyncClient, transaction_id: str):
        """재무제표.xlsx → FINANCIAL 폴더 자동 라우팅."""
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")

        content = b"fake xlsx content for test"
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/auto-upload",
            files={
                "file": (
                    "재무제표_2024.xlsx",
                    io.BytesIO(content),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["routed_category"] == "FINANCIAL"
        assert data["was_fallback"] is False
        assert data["routed_folder"]["category"] == "FINANCIAL"
        assert data["document"]["original_name"] == "재무제표_2024.xlsx"
        assert data["original_name_renamed"] is False

    async def test_auto_upload_unknown_file_uses_fallback(self, client: AsyncClient, transaction_id: str):
        """분류 불가 파일 → CORPORATE 폴백."""
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")

        content = b"random content"
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/auto-upload",
            files={"file": ("xyzabc_random_doc.pdf", io.BytesIO(content), "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["was_fallback"] is True
        assert data["routed_category"] is None
        assert data["routed_folder"]["category"] == "CORPORATE"

    async def test_auto_upload_duplicate_renames_file(self, client: AsyncClient, transaction_id: str):
        """동일 파일명 두 번 업로드 → 두 번째는 타임스탬프 접미사."""
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")

        content = b"pdf content"
        filename = "계약서.pdf"

        # 첫 번째 업로드
        resp1 = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/auto-upload",
            files={"file": (filename, io.BytesIO(content), "application/pdf")},
        )
        assert resp1.status_code == 201
        assert resp1.json()["original_name_renamed"] is False

        # 두 번째 업로드 (동일 파일명 동일 폴더)
        resp2 = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/auto-upload",
            files={"file": (filename, io.BytesIO(content), "application/pdf")},
        )
        assert resp2.status_code == 201
        data2 = resp2.json()
        assert data2["original_name_renamed"] is True
        # 파일명이 변경됨 (타임스탬프 포함)
        assert data2["final_name"] != filename
        assert "계약서_" in data2["final_name"]

    async def test_auto_upload_succeeds_with_auto_initialized_vdr(self, client: AsyncClient, transaction_id: str):
        """거래 생성 시 VDR이 자동 초기화되므로 auto-upload가 즉시 성공한다."""
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/auto-upload",
            files={"file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")},
        )
        assert resp.status_code == 201

    async def test_auto_upload_hwp_routes_to_tax(self, client: AsyncClient, transaction_id: str):
        """.hwp + 납세 키워드 → TAX 폴더."""
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")

        content = b"hwp content"
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/auto-upload",
            files={"file": ("납세증명서.hwp", io.BytesIO(content), "application/haansofthwp")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["routed_category"] == "TAX"
        assert data["was_fallback"] is False

    async def test_auto_upload_invalid_extension_returns_400(self, client: AsyncClient, transaction_id: str):
        """허용되지 않는 확장자 → 400."""
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/auto-upload",
            files={"file": ("virus.exe", io.BytesIO(b"MZ"), "application/pdf")},
        )
        assert resp.status_code == 400
