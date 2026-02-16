# Sprint 11: 보안/감사 + 운영

> 작성일: 2026년 02월 06일 15시 07분
> EPIC: EPIC 14 (외부배포본), EPIC 17 (보안), EPIC 18 (운영)
> Phase: Phase 4 (고급 기능)
> 상태: **COMPLETE** (Phase 1~4 전체 완료, 2026-02-08)

---

## 1. 개요

### 1.1 목표

| 구분 | 내용 |
|------|------|
| 목표 | RBAC + 감사로그 강화 + 외부배포본 마스킹 + 운영 파이프라인 |
| EPIC | EPIC 14, EPIC 17, EPIC 18 |
| MVP Story | FDD-1401~1405, FDD-1701~1705, FDD-1801~1805 |
| 의존성 | Sprint 7~10 완료 필수 |

**핵심 목표:**
- 역할 기반 접근 제어 (RBAC) v1 구현
- 감사 로그 강화 및 데이터 보존 정책
- 외부 공유용 마스킹 처리
- Report Generation Job 오케스트레이션

### 1.2 MVP Story

**EPIC 14 (외부배포본):**
- **FDD-1401**: Evidence Index 생성
- **FDD-1402**: 외부배포본 모드 정의
- **FDD-1403**: 민감정보 마스킹 엔진
- **FDD-1404**: 외부/내부 비교 검증
- **FDD-1405**: 민감정보 누출 테스트

**EPIC 17 (보안/감사):**
- **FDD-1701**: RBAC v1
- **FDD-1702**: 감사로그 v1 강화
- **FDD-1703**: 데이터 보존/파기 정책
- **FDD-1704**: 세션/토큰 관리
- **FDD-1705**: 권한 우회 테스트

**EPIC 18 (운영):**
- **FDD-1801**: Report Generation Job 오케스트레이션
- **FDD-1802**: 진행률 추적 API
- **FDD-1803**: 알림/웹훅 v1
- **FDD-1804**: 메트릭 수집 (관측성)
- **FDD-1805**: 장애 주입(Chaos) 10종

---

## 2. EPIC 17: 보안/감사추적

### 2.1 FDD-1701: RBAC v1

**수용기준 (AC):**
- [ ] 역할 정의: Admin, Manager, Analyst, Viewer
- [ ] 리소스별 권한 매트릭스
- [ ] API 엔드포인트 권한 검사
- [ ] UI 권한 기반 렌더링

**역할 정의:**

| 역할 | 설명 | 권한 수준 |
|------|------|----------|
| Admin | 시스템 관리자 | 전체 접근 + 설정 변경 |
| Manager | 딜 매니저 | 딜 생성/수정/삭제 + 승인 |
| Analyst | 분석가 | 딜 조회/수정 + 분석 실행 |
| Viewer | 열람자 | 딜 조회만 (읽기 전용) |

**권한 매트릭스:**

| 리소스 | Admin | Manager | Analyst | Viewer |
|--------|-------|---------|---------|--------|
| Deal CRUD | ✓ | ✓ | R/U | R |
| Definition Approve | ✓ | ✓ | - | - |
| Upload | ✓ | ✓ | ✓ | - |
| Mapping Approve | ✓ | ✓ | - | - |
| Report Generate | ✓ | ✓ | ✓ | - |
| Report Download | ✓ | ✓ | ✓ | ✓ |
| User Management | ✓ | - | - | - |
| Audit Log View | ✓ | ✓ | - | - |

**구현:**

```python
# backend/app/auth/rbac.py

class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"

class Permission(StrEnum):
    DEAL_CREATE = "deal:create"
    DEAL_READ = "deal:read"
    DEAL_UPDATE = "deal:update"
    DEAL_DELETE = "deal:delete"
    DEFINITION_APPROVE = "definition:approve"
    MAPPING_APPROVE = "mapping:approve"
    REPORT_GENERATE = "report:generate"
    REPORT_DOWNLOAD = "report:download"
    AUDIT_VIEW = "audit:view"
    USER_MANAGE = "user:manage"

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),  # 전체 권한
    Role.MANAGER: {
        Permission.DEAL_CREATE, Permission.DEAL_READ,
        Permission.DEAL_UPDATE, Permission.DEAL_DELETE,
        Permission.DEFINITION_APPROVE, Permission.MAPPING_APPROVE,
        Permission.REPORT_GENERATE, Permission.REPORT_DOWNLOAD,
        Permission.AUDIT_VIEW,
    },
    Role.ANALYST: {
        Permission.DEAL_READ, Permission.DEAL_UPDATE,
        Permission.REPORT_GENERATE, Permission.REPORT_DOWNLOAD,
    },
    Role.VIEWER: {
        Permission.DEAL_READ, Permission.REPORT_DOWNLOAD,
    },
}

def require_permission(permission: Permission):
    """권한 검사 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User, **kwargs):
            if not has_permission(current_user.role, permission):
                raise FDDError(ErrorCode.AUTH_FORBIDDEN)
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
```

---

### 2.2 FDD-1702: 감사로그 v1 강화

**수용기준 (AC):**
- [ ] 모든 CUD 작업 로깅
- [ ] 변경 전/후 값 저장
- [ ] 검색/필터 API
- [ ] 90일 보관 정책

**AuditLog 모델 확장:**

```python
# backend/app/models/audit.py (확장)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    # 기존 필드
    id: Mapped[uuid.UUID]
    entity_type: Mapped[str]
    entity_id: Mapped[uuid.UUID]
    action: Mapped[AuditAction]

    # 신규 필드
    user_id: Mapped[uuid.UUID | None]
    user_email: Mapped[str | None]
    user_role: Mapped[str | None]
    ip_address: Mapped[str | None]
    user_agent: Mapped[str | None]

    before_state: Mapped[dict | None] = mapped_column(JsonbColumn, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JsonbColumn, nullable=True)
    changed_fields: Mapped[list[str] | None] = mapped_column(JsonbColumn, nullable=True)

    session_id: Mapped[str | None]
    request_id: Mapped[str | None]

    # 보관 정책
    expires_at: Mapped[datetime | None]  # NULL = 영구 보관
```

**검색 API:**

```python
@router.get("/audit-logs")
def list_audit_logs(
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    action: AuditAction | None = None,
    user_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditLogListResponse:
    """감사 로그 검색"""
    ...
```

---

### 2.3 FDD-1703: 데이터 보존/파기 정책

**수용기준 (AC):**
- [ ] 데이터 유형별 보존 기간 정의
- [ ] 자동 파기 스케줄러
- [ ] 파기 전 알림
- [ ] 파기 로그 기록

**보존 정책:**

| 데이터 유형 | 보존 기간 | 파기 방식 |
|-------------|----------|----------|
| Deal (Complete) | 7년 | Hard Delete |
| Deal (Draft) | 90일 | Hard Delete |
| Audit Log | 7년 | Archive → Delete |
| Upload Files | 1년 | Hard Delete (with log) |
| Session Data | 30일 | Hard Delete |
| Report Files | 2년 | Archive → Delete |

**구현:**

```python
# backend/app/services/retention/policy.py

class RetentionPolicy:
    """데이터 보존 정책"""

    POLICIES = {
        "deal_complete": timedelta(days=365 * 7),
        "deal_draft": timedelta(days=90),
        "audit_log": timedelta(days=365 * 7),
        "upload_file": timedelta(days=365),
        "session": timedelta(days=30),
        "report": timedelta(days=365 * 2),
    }

    def get_expiry_date(self, data_type: str) -> datetime:
        """만료일 계산"""
        return datetime.utcnow() + self.POLICIES[data_type]

    def get_expired_items(self, data_type: str) -> list[Any]:
        """만료된 항목 조회"""
        ...

    def purge_expired(self, data_type: str, dry_run: bool = True) -> int:
        """만료 항목 파기"""
        ...
```

---

### 2.4 FDD-1704: 세션/토큰 관리

**수용기준 (AC):**
- [ ] JWT 기반 인증
- [ ] Refresh Token 지원
- [ ] 세션 만료 처리
- [ ] 동시 세션 제한

**구현 (향후 Auth0/Keycloak 통합 대비):**

```python
# backend/app/auth/token.py

JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(user: User) -> str:
    """Access Token 생성"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user: User) -> str:
    """Refresh Token 생성"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user.id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
```

---

## 3. EPIC 14: Appendix + 외부배포본

### 3.1 FDD-1401: Evidence Index 생성

**수용기준 (AC):**
- [ ] 보고서 내 모든 Evidence 인덱싱
- [ ] 페이지/위치 참조
- [ ] 유형별 그룹핑

**Evidence Index 구조:**

```python
class EvidenceIndexEntry(BaseModel):
    """Evidence 인덱스 항목"""
    evidence_id: str
    source_type: SourceType
    source_id: str
    source_detail: dict[str, Any]

    # 보고서 내 위치
    referenced_in: list[EvidenceReference]

class EvidenceReference(BaseModel):
    """Evidence 참조 위치"""
    section_id: str
    block_id: str
    row_index: int | None
    page_number: int | None  # 렌더링 후 계산

class EvidenceIndex(BaseModel):
    """Evidence 인덱스"""
    total_count: int
    by_source_type: dict[str, int]
    entries: list[EvidenceIndexEntry]
```

---

### 3.2 FDD-1402: 외부배포본 모드

**수용기준 (AC):**
- [ ] 내부용/외부용 모드 구분
- [ ] 외부용 제외 항목 정의
- [ ] 모드별 렌더링 분기

**모드 정의:**

| 모드 | 설명 | 포함 내용 |
|------|------|----------|
| INTERNAL | 내부용 | 전체 (이슈, 민감정보, 상세 근거) |
| EXTERNAL_BUYER | 매수자용 | 핵심 분석 + 제한된 근거 |
| EXTERNAL_SELLER | 매도자용 | 핵심 분석 + 제한된 근거 |
| REDACTED | 완전 마스킹 | 구조만 (숫자/텍스트 마스킹) |

---

### 3.3 FDD-1403: 민감정보 마스킹 엔진

**수용기준 (AC):**
- [ ] 금액 마스킹 (예: 1,234,567 → X,XXX,XXX)
- [ ] 텍스트 마스킹 (예: 삼성전자 → [회사A])
- [ ] 계정명 마스킹
- [ ] 마스킹 규칙 커스터마이징

**마스킹 엔진:**

```python
# backend/app/services/masking/engine.py

class MaskingEngine:
    """민감정보 마스킹 엔진"""

    def __init__(self, config: MaskingConfig):
        self.config = config

    def mask_amount(self, amount: Decimal) -> str:
        """금액 마스킹"""
        if self.config.amount_mode == "hide":
            return "[금액 숨김]"
        elif self.config.amount_mode == "range":
            return self._amount_to_range(amount)
        else:  # "x"
            return self._amount_to_x(amount)

    def mask_text(self, text: str, entity_type: str) -> str:
        """텍스트 마스킹"""
        if entity_type == "company":
            return self._get_company_alias(text)
        elif entity_type == "person":
            return "[인물]"
        elif entity_type == "account":
            return f"[계정{self._get_hash_suffix(text)}]"
        return text

    def mask_report_ir(self, report_ir: ReportIR) -> ReportIR:
        """Report IR 전체 마스킹"""
        ...
```

---

## 4. EPIC 18: 운영 (잡/큐/관측성)

### 4.1 FDD-1801: Report Generation Job 오케스트레이션

**수용기준 (AC):**
- [ ] 비동기 보고서 생성 Job
- [ ] 상태 추적 (Pending → Running → Complete/Failed)
- [ ] 재시도 로직 (최대 3회)
- [ ] 타임아웃 설정

**Job 모델:**

```python
# backend/app/models/job.py

class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobType(StrEnum):
    REPORT_GENERATE = "report_generate"
    DATA_INGEST = "data_ingest"
    ANOMALY_DETECT = "anomaly_detect"

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID]
    job_type: Mapped[JobType]
    status: Mapped[JobStatus]

    deal_id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID | None]

    input_params: Mapped[dict] = mapped_column(JsonbColumn)
    output_result: Mapped[dict | None] = mapped_column(JsonbColumn)
    error_message: Mapped[str | None]

    progress_percent: Mapped[int] = mapped_column(default=0)
    progress_message: Mapped[str | None]

    retry_count: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=3)

    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    timeout_seconds: Mapped[int] = mapped_column(default=600)

    created_at: Mapped[datetime]
```

---

### 4.2 FDD-1802: 진행률 추적 API

**수용기준 (AC):**
- [ ] Job 상태 조회 API
- [ ] 실시간 진행률 업데이트
- [ ] WebSocket 또는 SSE 지원 (선택)

**API:**

```python
@router.get("/jobs/{job_id}")
def get_job(job_id: UUID) -> JobRead:
    """Job 상태 조회"""
    ...

@router.get("/jobs/{job_id}/progress")
def get_job_progress(job_id: UUID) -> JobProgress:
    """Job 진행률 조회"""
    ...

@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: UUID) -> JobRead:
    """Job 취소"""
    ...
```

---

### 4.3 FDD-1804: 메트릭 수집 (관측성)

**수용기준 (AC):**
- [ ] API 응답 시간 측정
- [ ] Job 처리 시간 측정
- [ ] 에러율 추적
- [ ] Prometheus 포맷 export

**메트릭 정의:**

| 메트릭 | 유형 | 설명 |
|--------|------|------|
| `fdd_api_requests_total` | Counter | API 요청 수 |
| `fdd_api_request_duration_seconds` | Histogram | API 응답 시간 |
| `fdd_jobs_total` | Counter | Job 수 (상태별) |
| `fdd_job_duration_seconds` | Histogram | Job 처리 시간 |
| `fdd_errors_total` | Counter | 에러 수 (코드별) |
| `fdd_active_deals` | Gauge | 활성 Deal 수 |

---

## 5. 테스트 계획

### 5.1 테스트 목표

| 종류 | 목표 수 | 범위 |
|------|--------|------|
| RBAC 유닛 | 25 | 권한 검사 |
| AuditLog 유닛 | 15 | 로깅 |
| Masking 유닛 | 20 | 마스킹 엔진 |
| Job 유닛 | 20 | 상태 관리 |
| 보안 통합 | 15 | 권한 우회 테스트 (FDD-1705) |
| 성능/Chaos | 10 | 장애 주입 (FDD-1805) |
| **총계** | **105** | |

---

## 6. 구현 일정

### Phase 1 (Week 1-2): RBAC + Auth

- [ ] `backend/app/auth/rbac.py`
- [ ] `backend/app/auth/token.py`
- [ ] `backend/app/models/user.py` (확장)
- [ ] RBAC 테스트 (25개)

### Phase 2 (Week 3): Audit + Retention

- [ ] `backend/app/models/audit.py` (확장)
- [ ] `backend/app/services/retention/policy.py`
- [ ] Audit API 확장
- [ ] Audit 테스트 (15개)

### Phase 3 (Week 4): Masking + External

- [ ] `backend/app/services/masking/engine.py`
- [ ] 외부배포본 모드 구현
- [ ] Masking 테스트 (20개)

### Phase 4 (Week 5): Jobs + Observability

- [ ] `backend/app/models/job.py`
- [ ] `backend/app/services/jobs/orchestrator.py`
- [ ] 메트릭 수집
- [ ] Job 테스트 (20개) + Chaos 테스트 (10개)

---

## 7. 산출물 체크리스트

**코드:**
- [ ] `backend/app/auth/rbac.py`
- [ ] `backend/app/auth/token.py`
- [ ] `backend/app/models/user.py` (확장)
- [ ] `backend/app/models/audit.py` (확장)
- [ ] `backend/app/models/job.py`
- [ ] `backend/app/services/retention/policy.py`
- [ ] `backend/app/services/masking/engine.py`
- [ ] `backend/app/services/jobs/orchestrator.py`
- [ ] `backend/app/api/auth.py`
- [ ] `backend/app/api/jobs.py`

**마이그레이션:**
- [ ] `backend/alembic/versions/xxx_add_user_auth.py`
- [ ] `backend/alembic/versions/xxx_extend_audit_log.py`
- [ ] `backend/alembic/versions/xxx_add_jobs_table.py`

**테스트:**
- [ ] `backend/tests/auth/test_rbac.py`
- [ ] `backend/tests/auth/test_token.py`
- [ ] `backend/tests/masking/test_masking_engine.py`
- [ ] `backend/tests/jobs/test_job_orchestrator.py`
- [ ] `backend/tests/security/test_permission_bypass.py`
- [ ] `backend/tests/chaos/test_failure_injection.py`

---

## 8. 참조 파일

| 파일 | 용도 |
|------|------|
| `backend/app/models/audit.py` | 기존 AuditLog |
| `backend/app/core/logging.py` | 로깅 패턴 |
| `backend/app/core/exceptions.py` | 에러 처리 |
| `.github/workflows/ci.yml` | CI 파이프라인 확장 대상 |
