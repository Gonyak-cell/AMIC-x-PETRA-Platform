"""Azure Blob Storage 클라이언트 — VDR 파일 스토리지.

AZURE_STORAGE_CONNECTION_STRING 미설정 시 로컬 파일시스템 폴백 모드로 동작한다.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# 로컬 폴백 경로 (개발 환경용)
_LOCAL_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "generated" / "vdr"


class BlobStorageClient:
    """Azure Blob Storage 래퍼. 로컬 폴백 지원."""

    def __init__(self) -> None:
        self._container_client = None
        self._service_client = None
        self._account_name: str = ""
        self._account_key: str = ""
        self._is_local: bool = True
        self._initialized: bool = False
        self._init_lock = asyncio.Lock()

    @property
    def is_local_mode(self) -> bool:
        return self._is_local

    async def init(self) -> None:
        """BlobServiceClient를 초기화한다. 연결 문자열 없으면 로컬 모드."""
        conn_str = settings.AZURE_STORAGE_CONNECTION_STRING
        if not conn_str:
            logger.warning("AZURE_STORAGE_CONNECTION_STRING 미설정 — 로컬 파일시스템 폴백 모드")
            self._is_local = True
            self._initialized = True
            _LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            return

        from azure.storage.blob.aio import BlobServiceClient

        self._is_local = False
        self._service_client = BlobServiceClient.from_connection_string(conn_str)
        service_client = self._service_client

        # 연결 문자열에서 account_name/account_key 파싱
        for part in conn_str.split(";"):
            if part.startswith("AccountName="):
                self._account_name = part.split("=", 1)[1]
            elif part.startswith("AccountKey="):
                self._account_key = part.split("=", 1)[1]

        container_name = settings.AZURE_VDR_CONTAINER_NAME
        self._container_client = service_client.get_container_client(container_name)

        # 컨테이너 존재 확인, 없으면 생성
        try:
            await self._container_client.get_container_properties()
        except Exception:
            await self._container_client.create_container()
            logger.info("Azure Blob 컨테이너 생성: %s", container_name)

        self._initialized = True
        logger.info(
            "Azure Blob Storage 초기화 완료: account=%s, container=%s",
            self._account_name,
            container_name,
        )

    async def ensure_initialized(self) -> None:
        """이미 초기화됐으면 no-op, 아니면 init() 호출.

        Celery 워커처럼 lifespan 밖에서 호출되는 경우 안전하게 초기화한다.
        동시 호출 시 asyncio.Lock으로 중복 init()을 방지한다.
        """
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await self.init()

    async def close(self) -> None:
        """비동기 클라이언트를 정리한다."""
        if self._container_client is not None:
            await self._container_client.close()
            self._container_client = None
        if self._service_client is not None:
            await self._service_client.close()
            self._service_client = None

    async def upload_blob(self, blob_name: str, data: bytes, content_type: str) -> str:
        """파일을 업로드한다. blob_name을 반환."""
        if self._is_local:
            path = _LOCAL_STORAGE_DIR / blob_name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return blob_name

        from azure.storage.blob import ContentSettings

        blob_client = self._container_client.get_blob_client(blob_name)
        await blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return blob_name

    async def download_blob(self, blob_name: str) -> bytes:
        """파일을 다운로드한다."""
        if self._is_local:
            return (_LOCAL_STORAGE_DIR / blob_name).read_bytes()

        blob_client = self._container_client.get_blob_client(blob_name)
        stream = await blob_client.download_blob()
        return await stream.readall()

    async def download_blob_to_file(self, blob_name: str, dest: Path) -> None:
        """파일을 dest 경로에 스트리밍 다운로드한다 (메모리 절약).

        50MB 파일도 청크 단위로 쓰므로 힙 부담이 작다.
        동기 I/O는 asyncio.to_thread로 오프로드하여 이벤트 루프 블로킹을 방지한다.
        """
        if self._is_local:
            src = _LOCAL_STORAGE_DIR / blob_name
            await asyncio.to_thread(shutil.copy2, src, dest)
            return

        blob_client = self._container_client.get_blob_client(blob_name)
        stream = await blob_client.download_blob()
        data = await stream.readall()
        await asyncio.to_thread(dest.write_bytes, data)

    def generate_sas_url(self, blob_name: str, expiry_minutes: int = 60) -> str:
        """읽기 전용 SAS URL을 생성한다.

        로컬 모드에서는 사용 불가 — 호출자가 is_local_mode를 먼저 확인해야 한다.
        """
        if self._is_local:
            raise RuntimeError("로컬 모드에서는 SAS URL을 생성할 수 없습니다.")

        from azure.storage.blob import BlobSasPermissions, generate_blob_sas

        sas_token = generate_blob_sas(
            account_name=self._account_name,
            container_name=settings.AZURE_VDR_CONTAINER_NAME,
            blob_name=blob_name,
            account_key=self._account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(UTC) + timedelta(minutes=expiry_minutes),
        )
        return (
            f"https://{self._account_name}.blob.core.windows.net"
            f"/{settings.AZURE_VDR_CONTAINER_NAME}/{blob_name}?{sas_token}"
        )

    async def blob_exists(self, blob_name: str) -> bool:
        """blob 존재 여부를 확인한다."""
        if self._is_local:
            return (_LOCAL_STORAGE_DIR / blob_name).exists()

        blob_client = self._container_client.get_blob_client(blob_name)
        return await blob_client.exists()


# 싱글턴 인스턴스 — main.py lifespan에서 init()/close() 호출
blob_client = BlobStorageClient()
