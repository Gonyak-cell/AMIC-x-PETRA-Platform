# KOFIA DIS ProFrame API 마이그레이션

> 작성일: 2026-02-17 19:57
> 대상 모듈: `kiis/app/services/kofia_service.py`
> 상태: **완료**

---

## 1. 배경 및 문제

### 원래 구조
KOFIA DIS(전자공시서비스)에서 펀드 데이터를 수집하기 위해 `callServletService.jsp` 엔드포인트를 사용하고 있었다.

### 문제 발생
Docker 컨테이너 환경에서 KOFIA 서버의 WAF(Web Application Firewall)가 `callServletService.jsp`로의 모든 외부 요청을 차단했다.

- HTTP 200 OK는 반환되지만, 응답 본문이 WAF 차단 페이지
- 브라우저 헤더, TLS 핑거프린트, 세션 쿠키 등 모든 우회 방법 실패
- **핵심 발견**: `callServletService.jsp`는 서버 내부 전용 엔드포인트로, 외부에서는 어떤 방식으로든 접근 불가

---

## 2. 해결 방안 — ProFrame XML 프로토콜

### 발견 과정
Playwright를 사용하여 KOFIA DIS 웹사이트의 실제 브라우저 네트워크 트래픽을 캡처한 결과:

1. 브라우저는 `callServletService.jsp`를 사용하지 **않음**
2. 실제로는 **ProFrame XML 프로토콜**을 사용 (`/proframeWeb/XMLSERVICES/`)
3. 이 엔드포인트는 WAF 차단 없이 외부에서 접근 가능

### ProFrame XML 프로토콜 구조

**요청 형식:**
```xml
<?xml version="1.0" encoding="utf-8"?>
<message>
  <proframeHeader>
    <pfmAppName>FS-DIS2</pfmAppName>
    <pfmSvcName>{서비스명}</pfmSvcName>
    <pfmFnName>select</pfmFnName>
  </proframeHeader>
  <systemHeader></systemHeader>
  <DISCondFuncDTO>
    <tmpV30>{기준일}</tmpV30>
    ...
  </DISCondFuncDTO>
</message>
```

**응답 형식:**
```xml
<message>
  <DISCondFuncListDTO>
    <dbio_total_count_>25815</dbio_total_count_>
    <selectMeta>
      <tmpV1>운용사명</tmpV1>
      <tmpV2>펀드명</tmpV2>
      ...
    </selectMeta>
  </DISCondFuncListDTO>
</message>
```

### 핵심 발견: tmpV 제네릭 필드명
`DISCondFuncDTO`는 시맨틱 필드명(fundNm, companyCd 등)을 **사용하지 않는다**.
대신 `tmpV1`, `tmpV2`, ... `tmpV30` 등 제네릭 필드명을 사용한다.

41개 이상의 시맨틱 필드명을 시도했으나 모두 `"Unexpected element"` 에러 → Playwright 브라우저 캡처로 실제 필드명 발견.

---

## 3. 서비스별 tmpV 필드 매핑

### DISFundStdPriceSO (펀드 기준가격)
| 필드 | 의미 | 비고 |
|------|------|------|
| tmpV1 | 운용사명 | 출력 |
| tmpV2 | 펀드명 | 출력 |
| tmpV3 | 펀드유형 | 입/출력 (예: "혼합주식형") |
| tmpV4 | 설정일 | 출력 (YYYYMMDD) |
| tmpV5 | 설정액 | 출력 (백만원 단위) |
| tmpV6 | 기준가격 | 출력 (원) |
| tmpV12 | 표준코드 | 출력 (펀드 식별자) |
| tmpV13 | 운용사코드 | 출력 |
| tmpV14 | 기준일 | 출력 (YYYYMMDD) |
| tmpV30 | 기준일 | **입력** (YYYYMMDD) |

### DISFundFeeCmsSO (펀드 보수수수료)
| 필드 | 의미 | 비고 |
|------|------|------|
| tmpV1 | 운용사명 | 출력 |
| tmpV2 | 펀드명 | 출력 |
| tmpV5 | 운용보수(%) | 출력 |
| tmpV9 | 총비용비율(%) | 출력 |
| tmpV11 | 성과보수(%) | 출력 |
| tmpV15 | 표준코드 | 출력 (펀드 식별자) |
| tmpV30 | 기준일 | **입력** (월별 마지막 영업일) |

### DISNewEstSO (신규설정펀드)
| 필드 | 의미 | 비고 |
|------|------|------|
| tmpV1 | 운용사명 | 출력 |
| tmpV2 | 펀드명 | 출력 |
| tmpV3 | 설정일 | 출력 |
| tmpV10 | 표준코드 | 출력 |
| tmpV30 | 시작일 | **입력** (기간 검색) |
| tmpV31 | 종료일 | **입력** (기간 검색) |

### DISComStdYMDSO (기준일 조회)
| 필드 | 의미 | 비고 |
|------|------|------|
| codeDesc | 날짜유형코드 | 입력 (`D_RD` = 일별 기준가격일) |
| standardDt | 기준일 | 출력 (YYYYMMDD) |

---

## 4. 수수료 기준일 문제 및 해결

### 문제
- 가격 서비스(`DISFundStdPriceSO`)는 **일별** 기준일 사용 (예: `20260213`)
- 수수료 서비스(`DISFundFeeCmsSO`)는 **월별** 갱신
- `DISComStdYMDSO`의 `D_RD` 코드로 조회한 날짜(`20260213`)를 수수료 서비스에 사용하면 **0건** 반환

### 패턴 분석
| 날짜 | 수수료 건수 | 설명 |
|------|------------|------|
| 20260130 | 20,233 | 2026년 1월 마지막 영업일 (금) |
| 20260131 | 0 | 1월 31일 (토) — 비영업일 |
| 20251231 | 20,183 | 2025년 12월 마지막 영업일 (수) |
| 20251230 | 0 | — |
| 20251128 | 20,167 | 2025년 11월 마지막 영업일 (금) |

**결론**: 수수료 데이터는 **각 월의 마지막 영업일**에만 존재한다.

### 해결 — `_get_latest_fee_date()` 메서드
```python
async def _get_latest_fee_date(self) -> str:
    # 최근 3개월의 마지막 영업일 후보를 순서대로 시도
    for months_back in range(3):
        # 해당 월의 마지막 날 계산
        # 주말이면 금요일로 조정
        # 실제 데이터 존재 여부 확인 (ProFrame 요청)
        # 데이터 있으면 해당 날짜 캐시 후 반환
    # 폴백: 가격 기준일 사용
```

---

## 5. 수정 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `kiis/app/services/kofia_service.py` | **전면 재작성** | callServletService.jsp → ProFrame XML 프로토콜 |
| `kiis/app/utils/http_client.py` | 수정 | `bytes` data 및 `content` 파라미터 지원 추가 |
| `kiis/tests/test_kofia_service.py` | **전면 재작성** | ProFrame XML 기반 mock 테스트로 전환 |

---

## 6. kofia_service.py 주요 변경사항

### 삭제된 항목 (구 API)
- `callServletService.jsp` 기반 요청 로직
- JSON 응답 파싱 (`_parse_fund_list`, `_parse_fund_detail`, `_parse_managers`)
- Form-data POST 요청

### 추가된 항목 (ProFrame API)
- `_build_proframe_xml()` — ProFrame XML 요청 메시지 빌더
- `_parse_proframe_response()` — XML 응답 파서 (`<selectMeta>` + `<list>` 형식)
- `_request_proframe()` — ProFrame 엔드포인트 요청 메서드
- `_get_latest_standard_date()` — 가격 기준일 조회 (DISComStdYMDSO)
- `_get_latest_fee_date()` — 수수료 기준일 조회 (월별 마지막 영업일 탐색)
- `_get_all_fund_prices()` — 전체 펀드 가격 목록 캐시 조회
- `_get_all_fund_fees()` — 전체 펀드 수수료 목록 캐시 조회
- `_parse_fund_list_from_proframe()` — tmpV 필드 → FundListItem 변환
- `_parse_fund_detail_from_proframe()` — tmpV 필드 → FundItem 변환

### 유지된 항목
- `classify_fund_type()`, `classify_legal_type()`, `classify_asset_class()` — 분류 유틸리티
- `calculate_maturity_alert()` — 회수 집중 구간 계산
- `_apply_filters()`, `_apply_sort()` — 로컬 필터링/정렬
- `search_funds()`, `get_fund_detail()`, `get_fund_managers()` — 공개 API 시그니처

---

## 7. http_client.py 변경사항

```python
# 변경 전
async def post(self, url, *, json=None, data=None):
    return await self.request("POST", url, json=json, data=data)

# 변경 후
async def post(self, url, *, json=None, data=None):
    if isinstance(data, bytes):
        return await self.request("POST", url, content=data)  # XML bytes 직접 전송
    return await self.request("POST", url, json=json, data=data)
```

- `data` 파라미터 타입: `dict | None` → `dict | bytes | None`
- `request()` 메서드에 `content: bytes | None` 파라미터 추가
- `bytes` 데이터는 httpx의 `content` 파라미터로 전달 (raw body)

---

## 8. 테스트 결과

### 단위 테스트 (34개 전부 통과)
```
tests/test_kofia_service.py  34 passed in 3.26s
```

| 카테고리 | 테스트 수 | 상태 |
|---------|----------|------|
| 유틸리티 함수 (parse_date, parse_decimal 등) | 7 | PASSED |
| ProFrame XML 빌더/파서 | 4 | PASSED |
| 펀드 분류 (type, legal, asset) | 5 | PASSED |
| 회수 집중 구간 계산 | 5 | PASSED |
| 서비스 파싱 메서드 | 3 | PASSED |
| 필터/정렬 | 3 | PASSED |
| 서비스 통합 (mock) | 7 | PASSED |

### 실 API 통합 테스트

| 항목 | 결과 |
|------|------|
| 가격 데이터 (DISFundStdPriceSO) | **25,815건** (기준일 20260213) |
| 수수료 데이터 (DISFundFeeCmsSO) | **20,233건** (기준일 20260130) |
| 가격-수수료 코드 매칭 | **20,165건** (78% 매칭) |
| 펀드명 검색 ("삼성") | 2,985건 |
| 운용사명 검색 ("미래에셋") | 2,845건 |
| 자산클래스 필터 (부동산) | 553건 |
| 설정액 정렬 | 정상 (40조 → 8조 내림차순) |
| 한글 인코딩 | UTF-8 정상 |

### 상세 조회 예시
```
Code: KR5105487700
  Name: 삼성ABF코리아장기채권인덱스증권투자신탁[채권](A)
  Company: 삼성자산운용
  Mgmt fee: 0.14%
  Perf fee: 0.02%
  Est date: 2005-04-26
  Vintage: 2005
```

---

## 9. 아키텍처 참고

```
[프론트엔드] → [KIIS Backend API]
                    ↓
              KOFIAService
                    ↓
         ┌─────────────────────┐
         │  ProFrame XML       │
         │  /proframeWeb/      │
         │  XMLSERVICES/       │
         │                     │
         │  ├─ DISComStdYMDSO  │  기준일 조회
         │  ├─ DISFundStdPrice │  가격 목록 (일별)
         │  ├─ DISFundFeeCmsSO │  수수료 목록 (월별)
         │  └─ DISNewEstSO     │  신규설정 펀드
         └─────────────────────┘
              dis.kofia.or.kr
```

---

## 10. 향후 과제

| 항목 | 우선순위 | 설명 |
|------|---------|------|
| 운용인력 서비스 발견 | 중 | SDIS01008001000 페이지의 ProFrame 서비스 캡처 필요 |
| Docker 환경 통합 테스트 | 중 | 컨테이너 내에서 ProFrame API 정상 작동 확인 |
| 공휴일 처리 | 낮 | 현재 주말만 제외, 한국 공휴일은 미반영 |
| 수수료 기준일 캐시 TTL | 낮 | 월 1회 갱신이므로 TTL을 더 길게 설정 가능 |

---

## 11. 후속 이슈 — 모노레포 동기화 (2026-02-17 20:37)

### 문제
단독 KIIS 리포(`Coding/KIIS/`)에서 ProFrame 마이그레이션을 완료했으나, 모노레포(`AMIC x PETRA Platform/kiis/`)에 동기화하지 않아 Docker 컨테이너가 이전 코드를 실행했다.

### 증상
- Docker 내 `kofia_service.py`가 여전히 `callServletService.jsp` 사용
- 라우터 파라미터 불일치 (`fund_type` vs `fund_types`) → TypeError
- `except Exception`에서 잡혀 빈 DB 폴백 → 검색 결과 0건

### 해결
5개 파일을 단독 리포에서 모노레포로 복사:
- `app/services/kofia_service.py`
- `app/routers/kofia.py`
- `app/utils/http_client.py`
- `app/schemas/fund.py`
- `tests/test_kofia_service.py`

### 교훈
- 단독 리포에서 수정한 코드는 반드시 모노레포에도 동기화해야 함
- Docker 볼륨 마운트(`./kiis:/app`)는 모노레포 경로를 사용
- `except Exception` 블록에서 에러를 숨기면 디버깅이 극히 어려워짐

상세: `docs/20260217_2037_MSW_Removal_and_KIIS_Search_Fix.md`
