# VDR Azure Blob Storage 마이그레이션 플랜

> 작성: 2026-02-26 22:12:00

## Context

현재 VDR(Virtual Data Room) 파일 스토리지는 **Docker named volume (`vdr_storage`)**을 사용하여 Azure VM 로컬 디스크에 저장 중이다. 이는 VM 디스크 용량 한계, 백업 부재, 확장성 부재 문제가 있으며, production docker-compose에서 `volumes: []`로 덮어써서 실질적으로 **프로덕션에서 VDR 파일 지속성이 보장되지 않는 상태**이다.

**목표**: Azure Blob Storage (Korea Central)로 마이그레이션하여 안정적이고 확장 가능한 VDR 파일 스토리지를 구축한다.

**비용**: 초기 규모(~10GB) 기준 월 $1~5 수준.

---

## 수정 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `deal-mgmt/pyproject.toml` | `azure-storage-blob[aio]` 의존성 추가 |
| `deal-mgmt/app/core/config.py` | Azure 연결 문자열, 컨테이너명 설정 추가 |
| **NEW** `deal-mgmt/app/core/blob_storage.py` | Azure Blob 클라이언트 모듈 (업로드/다운로드/SAS URL) |
| `deal-mgmt/app/main.py` | lifespan에서 BlobServiceClient 초기화/종료 |
| `deal-mgmt/app/services/vdr_service.py` | upload_document: 파일시스템 → Blob 업로드 |
| `deal-mgmt/app/routers/vdr.py` | download: FileResponse → SAS URL 리다이렉트 |
| `deal-mgmt/app/routers/vdr_internal.py` | IM용 content 다운로드 엔드포인트 추가 + 버그 수정 |
| `im/src/api/tasks/vdr_extraction.py` | 공유 볼륨 → HTTP 다운로드 방식 전환 |
| `docker-compose.yml` | vdr_storage 볼륨 제거, Azure 환경변수 추가 |
| `docker-compose.prod.yml` | Azure 환경변수 추가 |
| **NEW** `deal-mgmt/scripts/migrate_vdr_to_blob.py` | 기존 로컬 데이터 → Blob 일회성 마이그레이션 |

---

## Phase 1: Azure Blob 클라이언트 모듈 (deal-mgmt)

### 1.1 의존성 추가 — `deal-mgmt/pyproject.toml`

dependencies에 추가:
```
"azure-storage-blob[aio]>=12.20.0",
```

### 1.2 설정 추가 — `deal-mgmt/app/core/config.py`

Settings 클래스에 필드 추가:
```python
# Azure Blob Storage (VDR)
AZURE_STORAGE_CONNECTION_STRING: str = ""
AZURE_VDR_CONTAINER_NAME: str = "amic-vdr"
```

### 1.3 Blob 클라이언트 — **NEW** `deal-mgmt/app/core/blob_storage.py`

`BlobStorageClient` 클래스:
- `azure.storage.blob.aio.ContainerClient` 래핑
- `init()` / `close()`: 비동기 생명주기 관리
- `upload_blob(blob_name, data, content_type)`: blob 업로드
- `download_blob(blob_name)`: blob 다운로드 (bytes 반환)
- `generate_sas_url(blob_name, expiry_minutes=60)`: 읽기 전용 SAS URL 생성 (1시간 만료)
- `is_local_mode` 속성: `AZURE_STORAGE_CONNECTION_STRING` 미설정 시 로컬 파일시스템 폴백 (개발용)
- Connection String 기반 인증 (Docker 환경에 적합)
- 싱글턴 인스턴스 `blob_client` 모듈 레벨 export

### 1.4 lifespan 초기화 — `deal-mgmt/app/main.py`

lifespan 함수에 추가:
```python
from app.core.blob_storage import blob_client
await blob_client.init()   # 컨테이너 존재 확인, 클라이언트 초기화
yield
await blob_client.close()  # 비동기 클라이언트 정리
```

---

## Phase 2: VDR 서비스 Blob 전환

### 2.1 업로드 — `deal-mgmt/app/services/vdr_service.py`

`upload_document()` (라인 202-241) 변경:
- **제거**: `VDR_STORAGE_DIR` 상수(라인 20), `storage_dir.mkdir()`(라인 220-221), `file_path.write_bytes()`(라인 224)
- **추가**: `blob_name = f"{txn_id}/{folder_id}/{stored_name}"` → `blob_client.upload_blob()` 호출
- **DB 저장**: `file_path` 컬럼에 blob name 저장 (절대 경로 대신)
  - 기존: `/app/generated/vdr/txn-id/folder-id/uuid.xlsx`
  - 변경: `txn-id/folder-id/uuid.xlsx`

> Alembic 마이그레이션 불필요 — `file_path` 컬럼(String(1000))의 의미만 변경, 타입 동일

### 2.2 다운로드 — `deal-mgmt/app/routers/vdr.py`

`download_document()` (라인 298-337) 변경:
- **제거**: `_SAFE_STORAGE_DIR`(라인 36), 경로 순회 검증(라인 318-325), `FileResponse`(라인 327-331)
- **추가**: SAS URL 생성 → `RedirectResponse(url=sas_url, status_code=307)`
- **로컬 모드 폴백**: `blob_client.is_local_mode`일 때 `Response(content=bytes)` 반환

> 프론트엔드 변경 불필요 — 브라우저가 307 리다이렉트를 자동 처리

---

## Phase 3: IM 모듈 통합 전환

### 3.1 내부 API — `deal-mgmt/app/routers/vdr_internal.py`

새 엔드포인트 추가:
```
GET /transactions/{txn_id}/documents/{doc_id}/content
```
- blob 콘텐츠 직접 스트리밍 (IM Celery worker용)
- 기존 `get_document_file_path` 엔드포인트는 deprecated 처리

**버그 수정** (발견): 라인 76에서 `VdrDocumentStatus.UPLOADED` (존재하지 않는 enum 값) → `VdrDocumentStatus.ACTIVE`로 수정.

### 3.2 IM VDR 추출 태스크 — `im/src/api/tasks/vdr_extraction.py`

- **제거**: `_VDR_SHARED_BASE = "/vdr-shared"` (라인 31)
- **제거**: `_resolve_vdr_file_paths()` 함수 (라인 115-151) — 파일시스템 경로 조회
- **추가**: `_download_vdr_documents()` — 내부 API `/content` 엔드포인트로 HTTP 다운로드 → `tempfile.NamedTemporaryFile`에 저장
- 추출 완료 후 임시 파일 정리 (`try/finally`)

> IM 모듈에 `azure-storage-blob` 의존성 추가 불필요 — deal-mgmt 내부 HTTP API를 통해 접근

---

## Phase 4: Docker Compose 정리

### 4.1 `docker-compose.yml`

- deal-mgmt-api, deal-mgmt-celery-worker에서 `vdr_storage:/app/generated/vdr` 마운트 제거
- im-api, im-celery-worker에서 `vdr_storage:/vdr-shared:ro` 마운트 제거
- volumes 섹션에서 `vdr_storage:` 선언 제거
- deal-mgmt 컨테이너에 `AZURE_STORAGE_CONNECTION_STRING` 환경변수 추가

### 4.2 `docker-compose.prod.yml`

- deal-mgmt-api 환경변수에 `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_VDR_CONTAINER_NAME` 추가

---

## Phase 5: 기존 데이터 마이그레이션 (일회성)

**NEW** `deal-mgmt/scripts/migrate_vdr_to_blob.py`:
1. DB에서 `file_path`가 절대 경로(`/app/generated/`)인 문서 조회
2. 로컬 파일 읽기 → Azure Blob 업로드
3. SHA256 해시 검증 (업로드 전후 일치 확인)
4. `file_path` 컬럼을 blob name으로 업데이트
5. 성공/실패 건수 리포트

---

## Phase 6: Azure 인프라 설정 (사용자 수동, 코드 작업 전 필요)

1. Azure Portal에서 Storage Account 생성
   - 리전: Korea Central (VM과 동일)
   - 성능: Standard
   - 중복: LRS (로컬 중복)
   - 접근 티어: Hot
2. 컨테이너 `amic-vdr` 생성 (Private 접근)
3. 연결 문자열 확보 → `.env`와 GitHub Secrets에 추가
4. 선택: Soft Delete 활성화 (7일 보존)

---

## 구현 순서 및 의존성

```
Phase 6 (Azure 인프라, 사용자 수동)
  ↓
Phase 1 (독립, 순수 추가)
  ↓
Phase 2 + Phase 3 (병렬 가능)
  ↓
Phase 4 (Phase 2+3 완료 후)
  ↓
Phase 5 (배포 후 일회성 실행)
```

---

## 리스크 및 대응

| 리스크 | 대응 |
|--------|------|
| SAS URL CORS 이슈 | 307 리다이렉트 대신 JSON으로 URL 반환 → 프론트에서 window.open() |
| 대용량 파일 업로드 타임아웃 | Azure SDK가 64MB 이상 자동 청킹 처리. 100MB 제한 내 안전 |
| IM Celery 다운로드 지연 | 일반적으로 <10MB Excel/PDF. 60초 타임아웃 충분 |
| 개발환경 Azure 미설정 | 로컬 파일시스템 폴백 모드 자동 전환 |
| 마이그레이션 중 데이터 유실 | SHA256 해시 검증 + 로컬 볼륨 즉시 삭제하지 않음 |

---

## 검증 방법

1. **로컬 테스트**: `AZURE_STORAGE_CONNECTION_STRING` 미설정 → 로컬 폴백 모드로 기존 동작 확인
2. **Azure 테스트**: 연결 문자열 설정 후 VDR 파일 업로드/다운로드 검증
3. **IM 연동 테스트**: VDR 문서 업로드 → IM 체크리스트 추출 태스크 실행 → 파싱 성공 확인
4. **tsc + vite build**: 프론트엔드 빌드 검증 (프론트 변경 없으므로 회귀 확인)
5. **배포 후**: 헬스체크 + VDR CRUD 수동 테스트
