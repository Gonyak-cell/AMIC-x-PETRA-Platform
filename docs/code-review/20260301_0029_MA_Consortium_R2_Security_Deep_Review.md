# Code Review R2 — MA 컨소시엄 보안 심층 리뷰

> **Review Date**: 2026-03-01 00:29
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: MA 컨소시엄/공동투자 매핑 (deal-mgmt + amic-platform)
> **Method**: R2 보안 심층 (OWASP Top 10 + STRIDE 위협 모델링) — 병렬 2-에이전트
> **Round**: R2 (이전: R1→R3→R4→R5→R6)

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|------------|----------|
| Major    | 4     | HIGH: 4    | P1: 4    |
| Moderate | 6     | HIGH: 5 / MEDIUM: 1 | P2: 6 |
| Minor    | 2     | MEDIUM: 2  | P3: 2    |
| **Total**| **12** | HIGH: **9** / MEDIUM: **3** | P1: **4** / P2: **6** / P3: **2** |

**에이전트**: backend-security-reviewer (OWASP Top 10) + STRIDE 위협 모델링
**교차 검증**: E-02 코드 직접 확인 (CONFIRMED)
**안전 확인**: SQL Injection ✓, Mass Assignment ✓, XSS ✓, Audit Logging ✓

---

## Findings

### [SEC-E02] create_consortium_mapping 딜 접근 검증 누락 — [Major/HIGH] — P1 (점수: 85)

- **위치**: `deal-mgmt/app/routers/consortium.py:104-110`
- **카테고리**: A01 Broken Access Control / Elevation of Privilege
- **교차 검증**: CONFIRMED — 코드 직접 Read 확인

**근거**:
```python
@router.post("/", response_model=ConsortiumMappingOut, status_code=201)
async def create_consortium_mapping(
    txn_id: uuid.UUID,
    body: ConsortiumMappingCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),  # ← RBAC만 체크
) -> ConsortiumMappingOut:
    # check_client_deal_access(db, txn_id, claims) 호출 없음
```

**문제**: `require_write_access()`는 RBAC 역할만 확인. CLIENT 역할은 이미 차단되지만, 향후 MEMBER/ADMIN 역할의 multi-tenancy에서 다른 딜에 매핑 생성 가능.
**영향**: 동일 파일의 다른 4개 엔드포인트(list, update, delete, summary)는 모두 `check_client_deal_access` 호출.
**수정 제안**: `_validate_buyer_in_txn` 호출 전에 `await check_client_deal_access(db, txn_id, claims)` 추가.

---

### [SEC-002] Excel 내보내기 Content-Disposition 헤더 인젝션 — [Major/HIGH] — P1 (점수: 70)

- **위치**: `deal-mgmt/app/routers/buyer_marketing.py:397-401`
- **카테고리**: A03 Injection

**근거**:
```python
filename = f"{txn.code_name or 'buyers'}_long_list.xlsx"
headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
```

**문제**: `txn.code_name`에 `"`, `\n`, `;` 등이 포함되면 HTTP 헤더 인젝션 가능. 예: `codename"; malicious-header: value` → 응답 분할.
**영향**: HTTP Response Splitting, 다운로드 파일명 조작.
**수정 제안**: RFC 5987 인코딩 적용 또는 `re.sub(r'[^\w\s.-]', '_', filename)` 새니타이징.

---

### [SEC-E01] 딜 간 Chinese Wall 미구현 — [Major/HIGH] — P1 (점수: 70)

- **위치**: `deal-mgmt/app/core/security.py` (check_client_deal_access 함수)
- **카테고리**: A01 Broken Access Control / Elevation of Privilege (구조적)

**문제**: `check_client_deal_access`는 CLIENT 역할만 제한. MEMBER/ADMIN은 모든 딜에 접근 가능. M&A에서 딜 간 정보 차단(Chinese Wall)이 없음.
**영향**: 현재 AMIC 내부 사용자만 접속하므로 즉각적 위험은 낮으나, 조직 확장 시 이해충돌 문제 발생 가능.
**성격**: 설계 리스크 (DESIGN_RISK) — 현재 운영 환경에서는 허용 가능하나 중기적으로 대응 필요.

---

### [SEC-S01] CSRF 방어 토큰 부재 — [Major/HIGH] — P1 (점수: 70)

- **위치**: `deal-mgmt/app/main.py` (전역)
- **카테고리**: A01 Broken Access Control / Spoofing

**문제**: CSRF 토큰 미적용. JWT가 httpOnly 쿠키로 전달되므로 CSRF 공격에 노출 가능.
**완화 요소**: `SameSite=Lax` 설정으로 POST/PATCH/DELETE CSRF는 차단됨. GET 기반 데이터 유출만 위험.
**영향**: GET 엔드포인트(목록 조회, Excel 다운로드)에 대한 CSRF 가능.
**수정 제안**: 중기적으로 CSRF 토큰(Double Submit Cookie 패턴) 도입. 단기적으로 `SameSite=Strict` 검토.

---

### [SEC-T01] notes/content 필드 길이 제한 없음 — [Moderate/HIGH] — P2 (점수: 40)

- **위치**: `deal-mgmt/app/schemas/consortium.py`, `deal-mgmt/app/schemas/marketing_log.py`
- **카테고리**: Tampering / DoS

**문제**: `notes: str | None`, `content: str | None` 필드에 `max_length` 미설정. 수 MB 문자열 전송 가능.
**수정 제안**: `Field(max_length=2000)` 또는 적절한 상한 설정.

---

### [SEC-T02] extra_data dict 크기 제한 없음 — [Moderate/HIGH] — P2 (점수: 40)

- **위치**: `deal-mgmt/app/schemas/buyer.py` (BuyerCandidateCreate/Update)
- **카테고리**: Tampering / DoS

**문제**: `extra_data: dict | None` — 임의 크기의 JSON 객체 수용. 중첩된 대형 객체 가능.
**수정 제안**: `model_validator`로 JSON 직렬화 크기 제한 (예: 10KB).

---

### [SEC-I01] CLIENT 역할의 매수자 연락처 노출 — [Moderate/HIGH] — P2 (점수: 40)

- **위치**: `deal-mgmt/app/routers/buyer.py` (list/detail 엔드포인트)
- **카테고리**: Information Disclosure

**문제**: CLIENT 역할이 `contact_email`, `contact_phone` 등 매수자 연락처를 조회 가능. 매도측 클라이언트에게 매수후보 연락처가 노출됨.
**영향**: M&A 딜에서 매수자 연락처는 민감 정보. 매도측 직접 접촉 리스크.
**수정 제안**: CLIENT 역할용 응답 스키마에서 연락처 필드 제외하거나 마스킹.

---

### [SEC-I02] Excel 내보내기 READ 권한 허용 — [Moderate/HIGH] — P2 (점수: 40)

- **위치**: `deal-mgmt/app/routers/buyer_marketing.py` (export_buyers_excel)
- **카테고리**: Information Disclosure

**문제**: Long-List Excel 내보내기가 READ 권한으로 가능. CLIENT 역할이 전체 매수자 목록을 Excel로 다운로드 가능.
**영향**: SEC-I01의 연락처 노출과 결합되면 전체 Long-List 유출.
**수정 제안**: WRITE 권한으로 상향하거나, CLIENT용 Excel에서 민감 컬럼 제외.

---

### [SEC-D01] 목록 API 페이지네이션 없음 — [Moderate/HIGH] — P2 (점수: 40)

- **위치**: `deal-mgmt/app/routers/buyer.py`, `consortium.py` (list 엔드포인트들)
- **카테고리**: DoS

**문제**: 매수자/컨소시엄 목록 조회에 페이지네이션 미적용. 대량 데이터 시 메모리/응답 시간 문제.
**완화 요소**: 딜당 매수자 수는 일반적으로 수십~수백 건으로 제한적.
**수정 제안**: `skip/limit` 파라미터 추가 (기존 KIIS 패턴 참조).

---

### [SEC-003] JWT exp 명시적 검증 미설정 — [Moderate/HIGH] — P2 (점수: 40)

- **위치**: `deal-mgmt/app/core/security.py` (JWT decode)
- **카테고리**: A07 Auth Failures

**문제**: `jwt.decode()` 호출 시 `options={"verify_exp": True}` 미명시. PyJWT 기본값은 True이지만 명시적 선언이 안전.
**영향**: 코드 리뷰 시 의도를 명확히 파악 가능. 실질적 취약점은 아님.
**수정 제안**: `options={"verify_exp": True}` 명시 추가.

---

### [SEC-004] 날짜 필드 패턴 검증 없음 — [Moderate/MEDIUM] — P3 (점수: 24)

- **위치**: `deal-mgmt/app/schemas/buyer.py` (BuyerCandidateUpdate)
- **카테고리**: A04 Insecure Design

**문제**: `ioi_date`, `loi_date` 등 날짜 필드가 `str | None`으로 정의. 유효하지 않은 날짜 문자열 저장 가능.
**완화 요소**: DB에 Text로 저장되어 런타임 오류는 없음. 프론트엔드 date picker가 유효 형식 강제.
**수정 제안**: `Field(pattern=r"^\d{4}-\d{2}-\d{2}$")` 추가.

---

### [SEC-005] Excel/DART 엔드포인트 Rate Limiting 없음 — [Minor/MEDIUM] — P3 (점수: 12)

- **위치**: `deal-mgmt/app/routers/buyer_marketing.py`, `deal-mgmt/app/routers/dart_integration.py`
- **카테고리**: DoS

**문제**: Excel 생성, DART API 검색 등 리소스 집약적 엔드포인트에 rate limiting 없음.
**완화 요소**: 인증 필수 + 내부 사용자만 접근. DART API 자체에 호출 제한 존재.
**수정 제안**: Nginx level rate limiting 또는 FastAPI `slowapi` 도입 (중기).

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)

| # | 이슈 | 요약 | 점수 |
|---|------|------|------|
| 1 | [SEC-E02] Major/HIGH | create_consortium 딜 접근 검증 누락 | 85 |
| 2 | [SEC-002] Major/HIGH | Excel Content-Disposition 헤더 인젝션 | 70 |
| 3 | [SEC-E01] Major/HIGH | Chinese Wall 미구현 (설계 리스크) | 70 |
| 4 | [SEC-S01] Major/HIGH | CSRF 토큰 부재 (SameSite=Lax 완화) | 70 |

### P2 — 개선 권장 (점수: 30-59)

| # | 이슈 | 요약 | 점수 |
|---|------|------|------|
| 5 | [SEC-T01] Moderate/HIGH | notes/content max_length 없음 | 40 |
| 6 | [SEC-T02] Moderate/HIGH | extra_data 크기 제한 없음 | 40 |
| 7 | [SEC-I01] Moderate/HIGH | CLIENT 연락처 노출 | 40 |
| 8 | [SEC-I02] Moderate/HIGH | Excel READ 권한 허용 | 40 |
| 9 | [SEC-D01] Moderate/HIGH | 목록 페이지네이션 없음 | 40 |
| 10 | [SEC-003] Moderate/HIGH | JWT exp 명시적 검증 미설정 | 40 |

### P3 — 저우선 (점수: <30)

| # | 이슈 | 요약 | 점수 |
|---|------|------|------|
| 11 | [SEC-004] Moderate/MEDIUM | 날짜 필드 패턴 검증 없음 | 24 |
| 12 | [SEC-005] Minor/MEDIUM | Rate Limiting 없음 | 12 |

---

## 안전 확인 (취약점 없음)

| 검사 항목 | 결과 | 확인 방법 |
|----------|------|----------|
| SQL Injection | ✅ 안전 | SQLAlchemy ORM 전용, 문자열 결합 쿼리 없음 |
| Mass Assignment | ✅ 안전 | Pydantic `model_dump(exclude_unset=True)` 패턴 |
| XSS | ✅ 안전 | React JSX 자동 이스케이프, `dangerouslySetInnerHTML` 미사용 |
| Audit Logging | ✅ 완비 | 모든 CUD에 `audit_service.record()` 호출 |
| Repudiation | ✅ 완비 | `created_by_email` + audit_log 조합 |

---

## Methodology

- **에이전트**: backend-security-reviewer (OWASP Top 10), STRIDE 위협 모델링 + 프론트엔드 보안
- **Files scanned**: consortium.py, buyer.py, buyer_marketing.py, dart_integration.py, security.py, main.py, schemas/*, ConsortiumPanel.tsx, ShortListOverview.tsx
- **Protocol**: Verified Claim Protocol v1.1
- **교차 검증**: E-02 코드 직접 Read 확인 (CONFIRMED)

## 수정 우선순위 권장

1. **즉시 수정 가능 (코드 1~3줄)**: SEC-E02 (접근 검증 추가), SEC-003 (JWT exp 명시)
2. **단기 수정 (함수 수정)**: SEC-002 (파일명 새니타이징), SEC-T01/T02 (필드 제한)
3. **설계 검토 필요**: SEC-E01 (Chinese Wall), SEC-S01 (CSRF), SEC-I01/I02 (CLIENT 권한 모델)
4. **중기 개선**: SEC-D01 (페이지네이션), SEC-005 (Rate Limiting)
