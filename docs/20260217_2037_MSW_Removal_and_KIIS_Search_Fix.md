# MSW 완전 제거 및 KIIS 펀드 검색 수정

> 작성일: 2026-02-17 20:37:46
> 관련 모듈: `amic-platform` (프론트엔드), `kiis` (백엔드)
> 상태: **완료**

---

## 1. 배경 및 문제

### 문제 1: MSW가 프로덕션에서 가짜 데이터 반환
- MSW(Mock Service Worker)가 개발 환경에서 모든 API 요청을 가로채 mock 데이터 반환
- `enableMocking()` 함수가 `main.tsx`에서 브라우저 Service Worker 등록
- 사용자가 실제 백엔드 데이터 대신 mock 데이터를 보게 되는 문제

### 문제 2: KIIS 펀드 검색이 0건 반환
- `http://localhost:8001/api/v1/kofia/funds?fund_name=삼성` → `total: 0`
- 이전 세션에서 KOFIA ProFrame 마이그레이션 완료했으나, 모노레포에 반영 안 됨
- Docker 컨테이너가 이전 코드(callServletService.jsp) 실행 중

---

## 2. MSW 제거 작업

### 2.1 이전 세션에서 완료 (main.tsx)
- `enableMocking()` 함수 전체 삭제
- MSW 동적 import (`import("./test/mocks/browser")`) 제거
- 직접 `createRoot().render()` 호출로 변경
- Stale Service Worker 정리 코드 추가

### 2.2 이번 세션에서 완료 (잔여 파일 제거)

| 파일 | 작업 | 설명 |
|------|------|------|
| `public/mockServiceWorker.js` | **삭제** | MSW Service Worker 스크립트 |
| `dist/mockServiceWorker.js` | **삭제** | 빌드 산출물 복사본 |
| `src/test/mocks/browser.ts` | **삭제** | 브라우저 MSW 설정 (`setupWorker`) |
| `package.json` | **수정** | `msw.workerDirectory` 설정 제거 |

### 2.3 유지된 파일 (단위 테스트 전용)

| 파일 | 용도 | 프로덕션 영향 |
|------|------|-------------|
| `src/test/mocks/server.ts` | Vitest Node.js 서버 (`setupServer`) | 없음 |
| `src/test/mocks/handlers.ts` | API 핸들러 정의 | 없음 |
| `src/test/mocks/data.ts` | Mock 데이터 | 없음 |
| `src/test/setup.ts` | Vitest 라이프사이클 | 없음 |
| `msw` (devDependencies) | NPM 패키지 | 없음 (devDependency) |

> **핵심**: `msw` 패키지와 테스트 파일은 Vitest 단위 테스트에서만 사용됨.
> Node.js `setupServer`는 브라우저에서 실행되지 않으므로 프로덕션에 영향 없음.

---

## 3. KIIS 백엔드 검색 수정

### 3.1 근본 원인 분석

**코드 동기화 문제**: 단독 KIIS 리포(`Coding/KIIS/`)에서 ProFrame 마이그레이션을 완료했으나, 모노레포(`AMIC x PETRA Platform/kiis/`)에 복사하지 않았음.

```
단독 리포 (새 코드)                 모노레포 (이전 코드)
─────────────────                 ─────────────────
kofia_service.py                  kofia_service.py
  → ProFrame XML                    → callServletService.jsp (WAF 차단)
  → _get_all_fund_prices()          → _request("SDIS01006001000", ...)
  → fund_types (복수)               → fund_type (단수)
```

Docker는 모노레포의 `./kiis`를 볼륨 마운트하므로 이전 코드가 실행됨.

### 3.2 세부 원인 — 3계층 캐싱의 예외 삼킴

모노레포의 `kofia.py` 라우터에는 3계층 캐싱 전략이 있었음:

```
1단계: DB 최신 데이터 확인 → fresh_count=0 → None 반환
2단계: KOFIA API 호출 → TypeError 발생! (fund_type vs fund_types)
  → except Exception: 에러 로깅 없이 3단계로
3단계: DB 폴백 → 빈 테이블 → total=0 반환
```

**TypeError**: 라우터가 `fund_type=fund_type`(단수)을 전달했으나, 새 서비스는 `fund_types=`(복수 리스트)를 기대 → TypeError 발생 → `except Exception`에서 잡혀 빈 DB 폴백.

### 3.3 해결 — 5개 파일 동기화

| 파일 | 변경 내용 |
|------|----------|
| `kiis/app/services/kofia_service.py` | ProFrame XML 버전으로 교체 |
| `kiis/app/routers/kofia.py` | 3계층 캐싱 라우터 → 단순 라우터로 교체 |
| `kiis/app/utils/http_client.py` | `bytes` data 및 `content` 파라미터 지원 |
| `kiis/app/schemas/fund.py` | 새 응답 스키마 동기화 |
| `kiis/tests/test_kofia_service.py` | ProFrame 기반 테스트 동기화 |

### 3.4 라우터 변경 비교

**이전 (3계층 캐싱 — 버그 있음)**:
```python
# 273줄, DB 의존, sync 메서드 필요
async def list_funds(..., db: AsyncSession = Depends(get_db)):
    db_result = await _query_fresh_funds_from_db(db, ...)  # DB 체크
    if db_result is not None:
        return db_result
    try:
        items, total = await service.search_funds(fund_type=fund_type, ...)  # TypeError!
        await service.sync_funds_to_db(db, items)  # 존재하지 않는 메서드
    except Exception:
        return await _fallback_funds_from_db(db, ...)  # 빈 DB
```

**이후 (직접 API 호출)**:
```python
# 93줄, DB 비의존, KOFIA API 직접 호출
async def list_funds(...):
    items, total = await service.search_funds(fund_types=_csv(fund_type), ...)
    return FundListResponse(total=total, page=page, size=size, items=items)
```

---

## 4. 검증 결과

### API 테스트

| 테스트 | 결과 |
|--------|------|
| `GET /kofia/funds?fund_name=삼성` | **2,985건** |
| `GET /kofia/funds?fund_name=삼성` (nginx :3000) | **2,985건** |
| Docker 내부 직접 호출 `search_funds(fund_name='삼성')` | **2,985건** |
| Redis 캐시 생성 | **8.6MB**, TTL 21,600초 |

### MSW 제거 확인

| 항목 | 상태 |
|------|------|
| `public/mockServiceWorker.js` | 삭제됨 |
| `browser.ts` | 삭제됨 |
| `main.tsx` enableMocking | 이미 제거됨 |
| `package.json` msw.workerDirectory | 제거됨 |
| Vitest MSW (server.ts) | 유지 (테스트 전용) |

---

## 5. 에이티유파트너스 관련

KOFIA DIS 데이터 범위 확인:
- `DISFundStdPriceSO` (기준가격): **89개 운용사**, 25,815개 펀드
- `DISNewEstSO` (신규설정): 3,264건

에이티유파트너스는 **기관전용 사모펀드 운용사**로, KOFIA DIS 기준가격 공시 대상에 포함되지 않음.

### 기관전용 사모펀드 데이터 조회 방안
1. **금감원 DART 전자공시** — 사모펀드 설정/해지 공시 조회
2. **KOFIA 사모펀드 정보** — 별도 서비스(`SDIS01007001000` 등) 확인 필요
3. **KIIS DB 직접 등록** — GP/운용사 정보 수동 입력

---

## 6. 수정 파일 요약

### 프론트엔드 (`amic-platform/`)

| 파일 | 변경 |
|------|------|
| `src/main.tsx` | MSW 시작 코드 제거 (이전 세션), stale worker 정리만 유지 |
| `src/test/mocks/browser.ts` | **삭제** |
| `public/mockServiceWorker.js` | **삭제** |
| `dist/mockServiceWorker.js` | **삭제** |
| `package.json` | `msw.workerDirectory` 제거 |

### 백엔드 (`kiis/`)

| 파일 | 변경 |
|------|------|
| `app/services/kofia_service.py` | ProFrame XML 버전으로 동기화 |
| `app/routers/kofia.py` | 3계층 캐싱 → 직접 API 호출로 교체 |
| `app/utils/http_client.py` | bytes data 지원 동기화 |
| `app/schemas/fund.py` | 응답 스키마 동기화 |
| `tests/test_kofia_service.py` | ProFrame 기반 테스트 동기화 |

---

## 7. 향후 과제

| 항목 | 우선순위 | 설명 |
|------|---------|------|
| 기관전용 사모펀드 데이터소스 | 높 | 에이티유파트너스 등 GP 정보 조회 방안 |
| 단독 리포↔모노레포 동기화 자동화 | 중 | git submodule 또는 CI 스크립트 |
| 3계층 캐싱 재도입 | 낮 | ProFrame 서비스 인터페이스에 맞춘 DB 캐싱 구현 |
| MSW devDependency 제거 검토 | 낮 | Vitest 테스트에서만 사용, 필요 시 제거 |
