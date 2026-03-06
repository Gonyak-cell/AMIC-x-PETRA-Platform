# VcCompany 매출 데이터 하이브리드 시딩 설계

> 작성: 2026-03-06 21:59 KST

## 목적

VcCompany (114,964건)의 `revenue`, `revenue_year` 필드를 공공데이터포털 기업재무정보로 채운다.

## 접근법: 하이브리드 (C안)

### Phase 1: SICompany → VcCompany 크로스레퍼런스

- SICompany에 이미 공공데이터 API로 수집된 매출 데이터를 VcCompany로 복사
- 매칭 키: `vc_companies.corp_reg_no = si_companies.jurir_no` (공백/하이픈 정규화)
- 복사 필드: `revenue`, `revenue_year`
- 조건: SICompany.revenue IS NOT NULL
- API 호출 0회, 수초 소요

### Phase 2: 잔여분 API 직접 호출

- Phase 1 미매칭 + corp_reg_no 있는 VcCompany 대상
- API: `GetFinaStatInfoService_V2` (공공데이터포털 금융위 기업재무정보)
- Rate limit: 90회/분, 배치 500건
- 연도 전략: 2024 우선 → 2023 fallback
- 추출 필드: `enpSaleAmt` → revenue (매출액)

## 스크립트

**파일**: `deal-mgmt/scripts/seed_vc_revenue_data.py`

**CLI**:
```
cd deal-mgmt
python -m scripts.seed_vc_revenue_data [--limit 9000] [--year 2024] [--phase1-only] [--phase2-only] [--force]
```

| 옵션 | 설명 |
|------|------|
| `--limit` | Phase 2 API 호출 최대 건수 (기본: 9000, 일일 한도 고려) |
| `--year` | 조회 사업연도 (기본: 2024) |
| `--phase1-only` | DB 크로스레퍼런스만 실행 |
| `--phase2-only` | API 호출만 실행 (Phase 1 이미 완료 시) |
| `--force` | 기존 매출 데이터 재수집 |

## 데이터 흐름

```
Phase 1: DB 내부 크로스레퍼런스
┌──────────────┐    corp_reg_no = jurir_no    ┌──────────────┐
│  VcCompany   │ ◄──────────────────────────  │  SICompany   │
│  (revenue=∅) │    revenue, revenue_year 복사 │  (revenue=✓) │
└──────────────┘                              └──────────────┘

Phase 2: 잔여분 API 호출
┌──────────────┐    corp_reg_no → crno        ┌──────────────┐
│  VcCompany   │ ◄──────────────────────────  │ data.go.kr   │
│  (revenue=∅) │    GetFinaStatInfoService_V2  │ 공공데이터API │
└──────────────┘                              └──────────────┘
```

## 에러 처리

- Phase 2 중단 시 이미 업데이트된 건은 보존 (청크 단위 커밋, 200건)
- `--limit`으로 API 일일 한도(10,000회) 초과 방지
- Rate limit: 분당 90회 (공식 100회의 90%)
- 연도 fallback: primary_year 실패 → primary_year - 1 재시도

## 기존 코드 재사용

- `seed_revenue_data.py`의 `_parse_items()`, `_check_result_code()`, `_parse_numeric()` 패턴 차용
- VcCompany는 revenue/revenue_year만 필요하므로 SICompany보다 단순

## 관련 파일

- `deal-mgmt/scripts/seed_revenue_data.py` — SICompany 재무정보 시딩 (참조)
- `deal-mgmt/scripts/seed_vc_companies.py` — VcCompany 기업개황 시딩 (Excel)
- `deal-mgmt/app/models/vc_company.py` — VcCompany 모델
- `deal-mgmt/app/models/si_company.py` — SICompany 모델
