"""VDR (Virtual Data Room) API 테스트."""

import io
import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


# ── Init ─────────────────────────────────────────────────────


class TestVdrInit:
    async def test_init_vdr_creates_default_folders(self, client: AsyncClient, transaction_id: str):
        resp = await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        assert resp.status_code == 201
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

    async def test_init_vdr_duplicate_returns_400(self, client: AsyncClient, transaction_id: str):
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        resp = await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")
        assert resp.status_code == 400

    async def test_init_vdr_invalid_txn_returns_404(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(f"/api/v1/transactions/{fake_id}/vdr/init")
        assert resp.status_code == 404


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
    async def test_vdr_summary_not_initialized(self, client: AsyncClient, transaction_id: str):
        resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["initialized"] is False
        assert data["total_folders"] == 0

    async def test_vdr_summary_after_init_and_upload(self, client: AsyncClient, transaction_id: str):
        await client.post(f"/api/v1/transactions/{transaction_id}/vdr/init")

        # 첫 번째 폴더에 파일 업로드
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
                "deal_type": "MA",
                "target_company_name": "격리 테스트",
                "client_name": "테스트",
                "side": "BUY",
                "lead_advisor_email": "test@example.com",
            },
        )
        txn2_id = txn2_resp.json()["id"]

        # 두 번째 거래의 VDR은 비어있어야 함
        resp = await client.get(f"/api/v1/transactions/{txn2_id}/vdr/folders")
        assert resp.status_code == 200
        assert len(resp.json()) == 0


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

    async def test_overview_shows_uninitialized(self, client: AsyncClient, transaction_id: str):
        """VDR 미초기화 거래는 vdr_initialized=false."""
        resp = await client.get("/api/v1/vdr/overview")
        items = resp.json()
        item = next(i for i in items if i["transaction_id"] == transaction_id)
        assert item["vdr_initialized"] is False
        assert item["total_folders"] == 0
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
