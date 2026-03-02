# MA 워크플로우 MOU 전환 — 13개 관점 통합 리뷰

> **대상**: `feat/ma-workflow` 브랜치 uncommitted 변경 41개 파일 (+814 / -343)
> **리뷰 시각**: 2026-03-02 14:31 KST
> **리뷰어**: Claude Opus 4.6 (5개 전문 에이전트 병렬 배포)

---

## 요약 대시보드

| 심각도 | 건수 | 즉시 차단 |
|--------|------|----------|
| **Critical** | 6 | 커밋 전 필수 수정 |
| **High** | 8 | 배포 전 필수 수정 |
| **Medium** | 14 | 배포 전 권장 수정 |
| **Low** | 8 | 점진적 개선 |
| **Info** | 2 | 참고 |
| **Pass** | 14 | 검증 통과 |

---

## 13개 관점별 이슈 매트릭스

| # | 관점 | Critical | High | Medium | Low | 대표 이슈 |
|---|------|----------|------|--------|-----|----------|
| 1 | 아키텍처/설계 | 0 | 1 | 2 | 2 | O1: ErrorBoundary 부재 |
| 2 | 보안 (OWASP) | 0 | 4 | 4 | 1 | SEC-1: 승인 결정 JWT 우회 |
| 3 | 성능 | 2 | 1 | 4 | 3 | PERF-1: VDR 메모리 전체 적재 |
| 4 | 에러 처리 | 0 | 1 | 2 | 0 | E1: 교체 삭제 실패 무피드백 |
| 5 | 타입 안전성 | 1 | 0 | 1 | 0 | TS-CR1: AuditLog entity_id 불일치 |
| 6 | DB/마이그레이션 | 2 | 0 | 3 | 1 | MIG-1: AuditLog 모델-서비스 불일치 |
| 7 | API 계약 | 0 | 0 | 2 | 1 | API-1: Rate Limiting 멀티워커 우회 |
| 8 | 테스트 | 0 | 0 | 0 | 1 | TEST-1: 매직바이트 실패 케이스 없음 |
| 9 | 접근성 (a11y) | 0 | 0 | 1 | 2 | AC-1: 포커스 트랩 미구현 |
| 10 | CI/CD | 0 | 0 | 0 | 0 | (이슈 없음) |
| 11 | 코드 품질/스타일 | 1 | 0 | 0 | 1 | CQ-1: float 비용 한도 |
| 12 | 동시성/경쟁조건 | 0 | 1 | 0 | 0 | CON-1: SPA 세션 멀티워커 불안정 |
| 13 | 관측성/로깅 | 0 | 0 | 0 | 1 | OBS-1: 에러 로그 민감 데이터 |

---

## Critical 이슈 (6건) — 커밋 전 필수 수정

### CR-1. AuditLog.entity_id 모델-서비스 타입 불일치
- **위치**: `deal-mgmt/app/models/audit.py:19` + `deal-mgmt/app/services/audit_service.py:88`
- **관점**: DB/마이그레이션, 타입 안전성
- **설명**: `AuditLog.entity_id`는 `Uuid` 타입이나, `audit_service.record()`는 `uuid.UUID | str`을 허용. Attachment 관련 감사 로그에서 문자열 `entity_id` 기록 시 PostgreSQL `UUID` 캐스팅 실패로 런타임 크래시.
- **영향**: Milestone 첨부파일 CRUD 시 감사 로그 기록 실패 → 500 에러
- **수정**: AuditLog.entity_id를 `String(100)`으로 변경 + 마이그레이션 055 생성, 또는 audit_service 호출 측에서 UUID만 전달하도록 제한

### CR-2. AuditLogRead Pydantic 스키마 불일치
- **위치**: `deal-mgmt/app/schemas/audit.py:16`
- **관점**: 타입 안전성, API 계약
- **설명**: `entity_id: uuid.UUID`로 선언. CR-1 수정 후 문자열 저장 시 Pydantic `ValidationError` 발생.
- **수정**: CR-1과 함께 `entity_id: str`로 변경

### CR-3. blob_storage.py — download_blob_to_file 위조 스트리밍
- **위치**: `deal-mgmt/app/core/blob_storage.py:149-151`
- **관점**: 성능
- **설명**: 주석은 "청크 단위 스트리밍"이나 실제 `stream.readall()`로 전체 메모리 적재. 50MB VDR 문서 다수 동시 다운로드 시 OOM 위험.
- **수정**: Azure SDK `chunks()` 비동기 이터레이터로 실제 청크 스트리밍 전환

### CR-4. vdr_service.py — upload_document 전체 파일 메모리 적재
- **위치**: `deal-mgmt/app/services/vdr_service.py:206`
- **관점**: 성능
- **설명**: 파라미터 시그니처가 `file_content: bytes`여서 호출 시점에 전체 파일이 메모리에 적재. attachments.py는 청크 스트리밍으로 개선되었으나 VDR은 미개선.
- **수정**: 스트리밍 업로드 패턴으로 전환 + SHA256 `update()` 반복 패턴 적용

### CR-5. approvals.py — 전체 PENDING 테이블 스캔
- **위치**: `deal-mgmt/app/routers/approvals.py:224-237`
- **관점**: 성능
- **설명**: `/approvals/pending/me` 엔드포인트가 모든 PENDING 승인 요청을 DB에서 전체 로드 후 Python에서 이메일 필터링. 딜 수 증가 시 O(n) 선형 성능 저하.
- **수정**: PostgreSQL JSONB `@>` 연산자 + GIN 인덱스로 DB 레벨 필터링

### CR-6. fm_tasks.py — LLM 비용 한도 float 사용
- **위치**: `deal-mgmt/app/tasks/fm_tasks.py:69`
- **관점**: 코드 품질
- **설명**: `ralph_max_cost_usd: float = 15.0` — 재무 제어 임계값에 float 사용. 이진 부동소수점 오차로 비용 한도 비교 부정확. `spa_analysis_service.py:46`에도 동일 패턴.
- **수정**: 내부 비교 시 `Decimal` 변환 후 사용

---

## High 이슈 (8건) — 배포 전 필수 수정

### H-1. 승인 결정 시 JWT 이메일 대신 요청 바디 이메일 신뢰
- **위치**: `deal-mgmt/app/routers/approvals.py:149`
- **관점**: 보안
- **설명**: `body.email`로 승인자 검증 → 인증된 사용자가 타인 이메일 위조 가능
- **수정**: `claims.email`로 검증 변경

### H-2. get_approval — 거래 범위 격리 누락
- **위치**: `deal-mgmt/app/routers/approvals.py:120-127`
- **관점**: 보안
- **설명**: UUID 추측으로 다른 거래의 승인 요청 열람 가능
- **수정**: `check_client_deal_access(db, approval.transaction_id, claims)` 추가

### H-3. 매직바이트 미등록 확장자 검증 우회
- **위치**: `deal-mgmt/app/routers/attachments.py:280-297`
- **관점**: 보안
- **설명**: `.m4a`, `.aac`, `.wma` 등 시그니처 미등록 확장자는 매직바이트 검증이 무력화
- **수정**: 미등록 확장자 기본 거부(deny-by-default) 또는 시그니처 추가

### H-4. 다중 확장자 파일명 처리 미흡
- **위치**: `deal-mgmt/app/routers/attachments.py:146-153`
- **관점**: 보안
- **설명**: `evil.php.pdf` → `.pdf`로 마지막 suffix만 확인, 다중 확장자 허용
- **수정**: `Path(name).suffixes` 개수 제한 (1개만 허용)

### H-5. MilestoneUploadPopover — 교체 삭제 실패 무피드백
- **위치**: `amic-platform/src/modules/ma/components/MilestoneUploadPopover.tsx:126-142`
- **관점**: 에러 처리
- **설명**: 새 파일 업로드 성공 + 기존 삭제 실패 시 중복 파일 발생, 사용자 무인지
- **수정**: 삭제 실패 시 경고 토스트 추가

### H-6. MA 모듈 ErrorBoundary 부재
- **위치**: `amic-platform/src/modules/ma/MaRoutes.tsx`
- **관점**: 아키텍처, 관측성
- **설명**: Docs/IM 모듈은 ErrorBoundary 적용, MA는 미적용 → 렌더링 에러 시 전체 백화면
- **수정**: `MaErrorBoundary` 생성 + 라우트 래핑

### H-7. cancel_approval — 요청자 외 취소 가능
- **위치**: `deal-mgmt/app/routers/approvals.py:192-216`
- **관점**: 보안
- **설명**: write 권한이 있는 임의 사용자가 다른 사람의 승인 요청 취소 가능
- **수정**: `approval.requester_email == claims.email` 검증 추가

### H-8. SPA Step 2 응답에 LLM HTML sanitize 미적용
- **위치**: `deal-mgmt/app/services/spa_analysis_service.py:922`
- **관점**: 보안
- **설명**: DB 저장(Step 3) 시에만 `sanitize_html()` 적용, Step 2 클라이언트 응답은 LLM 원본 HTML 그대로 반환 → XSS 가능
- **수정**: Step 2 반환 전 `sanitize_html()` 적용

---

## Medium 이슈 (14건) — 배포 전 권장 수정

| ID | 관점 | 위치 | 설명 |
|----|------|------|------|
| M-1 | 보안 | `docker-compose.prod.yml:131,208,294` | Redis 기본 패스워드 `redis` — 프로덕션에서 약한 기본값 |
| M-2 | 보안 | `docker-compose.prod.yml:147` | Elasticsearch 기본 패스워드 `changeme` |
| M-3 | 보안 | `docker-compose.prod.yml:319` | Celery 워커에 JWT Secret 불필요 노출 |
| M-4 | 성능 | `attachments.py:161` | 동기 `mkdir` 이벤트 루프 블로킹 → `asyncio.to_thread()` |
| M-5 | 성능 | `attachments.py:176-177` | aiofiles 컨텍스트 내 수동 `f.close()` → 이중 close 위험 |
| M-6 | 성능 | `workflow_engine.py:291-306` | risk_items/compliance_items 복합 인덱스 누락 |
| M-7 | 성능 | `fm_tasks.py:27-28` | ThreadPoolExecutor 매 호출 생성 → 싱글턴 캐싱 |
| M-8 | 성능 | `docker-compose.prod.yml:309` | Celery concurrency=2 + DB pool_size=10 불균형 |
| M-9 | 성능 | `docker-compose.prod.yml:289` | Redis 256MB allkeys-lru — 30분 FM 결과 소실 위험 |
| M-10 | 에러 처리 | `blob_storage.py:67` | `Exception` 광역 포획 → 인증 오류 삼킴 |
| M-11 | 에러 처리 | `vdr_service.py:239-244` | 이중 Exception 광역 포획, 두 번째는 삼킴 |
| M-12 | 타입 안전성 | `TransactionWorkspacePage.tsx:468,1051` | `PhaseMilestone` → `UploadableMilestone` narrowing 미흡 |
| M-13 | 접근성 | `MilestoneUploadPopover.tsx:46-72` | 포커스 트랩 미구현 (WAI-ARIA Dialog 규격) |
| M-14 | 아키텍처 | `TransactionWorkspacePage.tsx` (2000줄+) | God Component — 탭별 분리 필요 |

---

## Low 이슈 (8건) — 점진적 개선

| ID | 관점 | 위치 | 설명 |
|----|------|------|------|
| L-1 | 코드 품질 | `approvals.py` 전체 | 7개 라우터 함수 반환 타입 힌트 누락 |
| L-2 | 코드 품질 | `vdr_service.py:283` | `get_vdr_summary` 반환 `dict` 미구체화 |
| L-3 | 아키텍처 | `constants.ts` (910줄) | 전 도메인 상수 단일 파일 집중 |
| L-4 | 아키텍처 | 8개 파일 | STATUS_VARIANT 매핑 중복 (DRY 위반) |
| L-5 | 테스트 | `test_workflow.py` | 매직바이트 불일치 실패 케이스 테스트 없음 |
| L-6 | 접근성 | `PipelineFlow.tsx:53-138` | 화살표 키보드 내비게이션 부재 |
| L-7 | 동시성 | `useAttachments.ts:45` | enabled 패턴 불일치 (의도적일 수 있음) |
| L-8 | 관측성 | `log_decorators.py:82-88` | 에러 로그에 `notes` 등 비즈니스 민감 데이터 포함 |

---

## Info (2건) — 참고

| ID | 관점 | 위치 | 설명 |
|----|------|------|------|
| I-1 | 아키텍처 | `PipelineFlow.tsx:47-49` | phaseMilestoneMap 1:1 제한 (확장 시 주의) |
| I-2 | DB | `migrations/054` | PostgreSQL ALTER COLUMN 시 ACCESS EXCLUSIVE 락 (소규모 데이터는 무시 가능) |

---

## 검증 통과 (14건)

- [x] SQL 인젝션 방어 — 모든 쿼리 SQLAlchemy ORM/sa.text 바인드 파라미터 사용
- [x] 하드코딩 시크릿 없음 — 모든 시크릿 환경변수 참조
- [x] `Optional[X]` 대신 `X | None` 일관 사용
- [x] Pydantic v2 ConfigDict 패턴 적용
- [x] 파일 경로 순회 공격 방어 (`relative_to(UPLOAD_DIR)` + `_LOCAL_STORAGE_DIR` 검증)
- [x] 확장자 화이트리스트 + 매직바이트 이중 검증 구조
- [x] 청크 스트리밍 업로드 (attachments.py — 64KB 단위)
- [x] 페이지네이션 적용 (list_attachments, list_approvals)
- [x] 감사 로그 Enum/UUID/Decimal 직렬화 안전 (`_sanitize_for_json`)
- [x] N+1 방지 (`_check_risk_compliance_gate` COUNT 쿼리)
- [x] 마이그레이션 down_revision 체인 정확 (052 → 053 → 054)
- [x] UP041 준수 (`TimeoutError` 직접 사용)
- [x] 워크플로우 2단계 이상 건너뛰기 차단 (`diff not in (1, -1)`)
- [x] MOU_SIGNED deprecated 호환 처리 (PHASE_TAB_MAP, PHASE_VISIBLE_TABS)

---

## 수정 우선순위 권장

### Tier 0 (커밋 전 — 런타임 크래시 방지)
1. **CR-1 + CR-2**: AuditLog entity_id 타입 통일 (모델 + 스키마 + 마이그레이션 055)

### Tier 1 (배포 전 — 보안/안정성)
2. **H-1**: 승인 결정 JWT 이메일 검증
3. **H-2**: get_approval 거래 범위 격리
4. **H-7**: cancel_approval 요청자 검증
5. **H-3 + H-4**: 매직바이트 deny-by-default + 다중 확장자 차단
6. **H-8**: SPA Step 2 sanitize_html 적용
7. **CR-5**: approvals JSONB GIN 인덱스 + DB 필터링

### Tier 2 (배포 후 조기 — 성능/안정성)
8. **CR-3 + CR-4**: blob_storage/vdr_service 스트리밍 전환
9. **H-5**: 교체 삭제 실패 토스트
10. **H-6**: MaErrorBoundary 생성
11. **M-5**: aiofiles 이중 close 수정
12. **M-10 + M-11**: Exception 광역 포획 범위 축소

### Tier 3 (점진적 개선)
13. 나머지 Medium/Low 이슈

---

## 부록: 에이전트 배포 현황

| 에이전트 | 유형 | 검토 파일 수 | 이슈 수 |
|---------|------|------------|--------|
| 보안 리뷰 | backend-security-reviewer | 16 | 21 |
| DB 마이그레이션 검증 | migration-validator | 8 | 8 |
| 백엔드 성능 분석 | performance-profiler | 12 | 12 |
| Python 코드 품질 | python-code-reviewer | 16 | 18 |
| 프론트엔드 종합 | general-purpose | 12 | 11 |
| **합계 (중복 제거 후)** | | **41** | **38** |
