# VDR Azure Blob Storage 배포 완료 보고서

> 작성: 2026-02-26 23:32

## 개요

VDR(Virtual Data Room) 파일 스토리지를 Docker named volume(`vdr_storage`)에서 Azure Blob Storage로 마이그레이션하여 프로덕션 배포를 완료하였다.

## 변경 범위

### 1. Azure Blob Storage 클라이언트 모듈 (신규)

- **파일**: `deal-mgmt/app/core/blob_storage.py` (137줄)
- `BlobStorageClient` 클래스: Azure/로컬 폴백 지원
- 메서드: `init()`, `close()`, `upload_blob()`, `download_blob()`, `generate_sas_url()`, `blob_exists()`
- 싱글턴 인스턴스 `blob_client` — `main.py` lifespan에서 init/close 관리
- `AZURE_STORAGE_CONNECTION_STRING` 미설정 시 로컬 파일시스템 폴백 (`generated/vdr/`)

### 2. VDR 다운로드 방식 전환

- **파일**: `deal-mgmt/app/routers/vdr.py`
- 기존: `FileResponse` (서버에서 파일 직접 전송)
- 변경: Azure 모드 → SAS URL `RedirectResponse(status_code=307)` / 로컬 모드 → `Response` 직접 반환
- Content-Disposition 한글 파일명 RFC 6266 인코딩 적용 (`filename*=UTF-8''`)

### 3. 내부 API (IM ↔ deal-mgmt)

- **파일**: `deal-mgmt/app/routers/vdr_internal.py`
- `/file-path` → `/content` 엔드포인트 전환 (공유 볼륨 경로 → Blob 다운로드)
- 예외 처리 개선: `FileNotFoundError` → 404, 기타 → 502 분리
- `VdrDocumentStatus.UPLOADED` → `VdrDocumentStatus.ACTIVE` 수정

### 4. IM VDR 추출 태스크

- **파일**: `im/src/api/tasks/vdr_extraction.py`
- 공유 Docker 볼륨 직접 접근 → HTTP 내부 API 다운로드 전환
- 임시 파일 생성 + `finally` 블록에서 정리

### 5. VDR 서비스 업로드 경로

- **파일**: `deal-mgmt/app/services/vdr_service.py`
- `VDR_STORAGE_DIR` 로컬 경로 제거 → `blob_client.upload_blob()` 사용
- Blob 경로 패턴: `{transaction_id}/{folder_id}/{stored_name}`

### 6. Docker Compose

- **`docker-compose.yml`**: `vdr_storage` 볼륨 제거 (4개 서비스), Azure 환경변수 추가
- **`docker-compose.prod.yml`**: `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_VDR_CONTAINER_NAME` 추가

### 7. 의존성

- **`deal-mgmt/pyproject.toml`**: `azure-storage-blob[aio]>=12.20.0` 추가

### 8. 마이그레이션 스크립트 (신규)

- **파일**: `deal-mgmt/scripts/migrate_vdr_to_blob.py` (241줄)
- 기존 로컬 VDR 파일 → Azure Blob 일회성 마이그레이션
- dry-run 지원, SHA256 해시 검증, DB `file_path` 업데이트

## Azure 인프라 설정

| 항목 | 값 |
|------|-----|
| Storage Account | `amicplatformstorage` |
| 리소스 그룹 | `amic-platform-rg` |
| 위치 | Korea Central (보조: Korea South) |
| 성능 | 표준 |
| 복제 | RA-GRS |
| 계정 종류 | StorageV2 (범용 v2) |
| 컨테이너명 | `amic-vdr` |
| 공용 액세스 | 프라이빗 (익명 액세스 없음) |
| Blob 일시 삭제 | 7일 |
| 최소 TLS | 1.2 |
| 생성일 | 2026-02-26 |

## 프로덕션 서버 설정

| 항목 | 상태 |
|------|------|
| `.env`에 `AZURE_STORAGE_CONNECTION_STRING` 추가 | ✅ |
| `.env`에 `AZURE_VDR_CONTAINER_NAME=amic-vdr` 추가 | ✅ |
| `deal-mgmt-api` 재빌드 + 재시작 | ✅ |
| `deal-mgmt-celery-worker` 재빌드 + 재시작 | ✅ |
| Azure Blob Storage 초기화 로그 확인 | ✅ `account=amicplatformstorage, container=amic-vdr` |
| 헬스체크 (직접 + nginx) | ✅ `{"status":"ok","db":"ok"}` |

## 커밋 이력

| 커밋 | 설명 |
|------|------|
| `959eac8` | `feat(deal-mgmt/vdr): migrate VDR storage from Docker volume to Azure Blob Storage` |
| `207c19e` | `refactor(deal-mgmt): lint fixes, import cleanup, and Ralph/LDD improvements` |
| `40c6a22` | `feat(kiis,im): PEF registry service, IM template engine, and checklist improvements` |
| `3f286a9` | `chore: update Claude tooling hooks, skills, and daily report scripts` |
| `5d6ffc5` | `feat(im): add doc_type_resolver task and template engine test update` |

## 코드 리뷰 결과 (배포 전 수행)

- **테스트**: 764 passed, 14 skipped (deal-mgmt 전체)
- **Lint**: ruff clean (UP017, E402 수정 완료)
- **프론트엔드**: tsc --noEmit OK, vite build OK

### 발견 이슈 및 조치

| 심각도 | 이슈 | 조치 |
|--------|------|------|
| Major | Content-Disposition 한글 파일명 인코딩 누락 | ✅ 수정 — `urllib.parse.quote()` + `filename*=UTF-8''` |
| Moderate | vdr_internal.py 예외 처리 범위가 넓음 | ✅ 수정 — FileNotFoundError→404, Exception→502 분기 |
| Moderate | deal-mgmt-celery-worker prod override 부재 | ⏳ 별도 작업 — 마이그레이션 이전부터 존재 |
| Minor | blob_storage.py 로컬 모드 예외 미래핑 | 유지 — 현재 동작에 영향 없음 |
| Minor | _INTERNAL_SERVICE_KEY 빈 문자열 통과 가능성 | 유지 — Docker 기본값으로 실질 위험 없음 |

## 거래별 VDR 분리 아키텍처

현재 구현은 **6개 레이어에서 거래(Transaction)별 완전 분리**:

1. **DB 모델**: `transaction_id` FK + CASCADE + 인덱스
2. **쿼리 레이어**: 모든 함수에 `WHERE transaction_id` 필터
3. **API 인증**: `_get_and_authorize_txn()` — ADMIN/ADVISOR/CLIENT 역할별 접근 제어
4. **Blob 경로**: `{transaction_id}/{folder_id}/{stored_name}` 디렉토리 분리
5. **내부 API**: 서비스 키 + transaction_id 이중 보호
6. **프론트엔드**: React Query 캐시 키에 txnId 포함

## 향후 작업

- [ ] GitHub Secrets에 `AZURE_STORAGE_CONNECTION_STRING` 추가 (CI/CD 자동 배포용)
- [ ] Azure Portal에서 Storage Account 키 순환 정책 설정 (보안)
- [ ] deal-mgmt-celery-worker prod override 추가 (restart policy, 로깅 제한)
- [ ] 기존 로컬 VDR 파일 마이그레이션 실행 (해당 시 `migrate_vdr_to_blob.py`)
