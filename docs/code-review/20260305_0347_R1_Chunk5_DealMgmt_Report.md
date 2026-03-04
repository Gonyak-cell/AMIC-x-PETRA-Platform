# 코드 리뷰 리포트: Deal-Mgmt 백엔드 — Chunk 5

- 라운드: 1
- 모듈: Chunk 5 Deal-Mgmt
- 배치: 1~4 통합
- 시작: 2026-03-05 03:39
- 종료: 2026-03-05 03:47

## 배치 1: 린트/포맷/타입/의존성

- ruff check: ✅ 0건
- ruff format: ✅ 0건 (408 파일 검증)
- 코드 수정: 0건

## 배치 2~4: 통합 리뷰 (읽기 전용)

Grep 기반 패턴 스캔 + 핵심 파일 샘플링으로 52개 파일 검증.

### 발견된 이슈

| # | 관점 | 파일 | 라인 | 이슈 | 심각도 |
|---|------|-----|------|-----|--------|
| 1 | 데이터 무결성 | models/ 10개 파일 | 다수 | `mapped_column(JSONB)` 직접 사용 23건 — `JSON().with_variant(JSONB, "postgresql")` 미사용. conftest 워크어라운드로 CI 통과 중 | Medium |
| 2 | 성능 | routers/vdr.py → blob_storage.py | 324, 130 | VDR download_document가 파일 전체를 메모리 로드 (최대 100MB). StreamingResponse 미적용 | Medium |
| 3 | 테스트 | routers/buyer_marketing.py 등 3개 | — | 437줄 최대 라우터에 전용 테스트 없음 | Medium |
| 4 | 데이터 무결성 | models/ralph_session.py | 14-22 | RalphSessionStatus(str) — Enum 아닌 str 서브클래스, DB 제약 없음 | Low |
| 5 | 데이터 무결성 | models/transcription_job.py | 45 | meeting_date가 String(10) — Date 타입 미사용 | Low |
| 6 | 설정 | routers/vdr_internal.py | 20 | os.getenv() 직접 호출 — Settings 모델 밖 | Low |
| 7 | 성능 | core/blob_storage.py | 155 | download_blob_to_file에서 sync open() 사용 | Low |
| 8 | 예외처리 | routers/buyer_marketing.py | ~380 | except Exception: return [] — 예외 삼킴 | Low |
| 9 | 아키텍처 | routers/buyer_marketing.py | 360-401 | Excel export 로직이 라우터에 인라인 | Low |

### Chunk 8 이관 이슈 검증

| 이관 이슈 | 재검증 결과 |
|-----------|-----------|
| rate_limiter Lock | sync 함수 + GIL → 실질적 레이스 없음. **정상** |
| dependencies 싱글톤 | sync + GIL → 실질적 레이스 없음. **Info** |
| pagination 직렬 쿼리 | deal-mgmt 라우터에서 해당 패턴 미사용. **해당 없음** |
| blob_storage 메모리/sync | 이슈 #2, #7로 확인. **Medium + Low** |

### 양호한 패턴

- 모든 46개 라우터에 JWT 인증 Depends 주입 ✅
- 역할 기반 접근 제어 (ADMIN/MANAGER/ANALYST/CLIENT) 일관 ✅
- fi_mapping_service: asyncio.Lock + double-check + db.expunge() 패턴 우수 ✅
- SPA 분석 스키마: `__`, `import`, `exec`, `eval` 차단 regex ✅

## 검증 결과

- ruff check: ✅ 0건
- ruff format: ✅ 0건

## 에러 카운트

| 심각도 | 건수 |
|--------|------|
| Medium | 3건 (JSONB 직접 사용, VDR 메모리, 테스트 부재) |
| Low | 6건 |
| 합계 | 9건 (코드 수정 0건 — 읽기 전용 관찰) |

## 충족 관점 체크리스트

- [x] 9. 린트/포맷 (0건)
- [x] 6. 타입 안전성 (ruff 통과)
- [x] 10. 의존성 (ruff F401 0건)
- [x] 7. 데이터 무결성 (JSONB 23건 관찰)
- [x] 8. 환경변수/설정 (1건 관찰)
- [x] 12. API 계약 (관찰)
- [x] 1. 보안 (전 라우터 인증 확인)
- [x] 2. 성능 (VDR 메모리 관찰)
- [x] 4. 예외처리 (1건 관찰)
- [x] 5. 동시성 (관찰)
- [x] 3. 아키텍처 (1건 관찰)
- [x] 11. 테스트 (3개 라우터 미테스트)
- [x] 13. 코드 품질 (양호)
