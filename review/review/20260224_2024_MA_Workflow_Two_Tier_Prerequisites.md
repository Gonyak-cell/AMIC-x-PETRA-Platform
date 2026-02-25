# MA 워크플로우 전제 조건 2-Tier 분리 + 자동 전환 알림

> 작성: 2026-02-24 20:24:00

## 변경 요약

M&A 워크플로우 엔진의 전제 조건 시스템을 **단일 티어(hard blocker)** → **2-Tier(REQUIRED / RECOMMENDED)** 로 분리하고, 조건 충족 시 자동 알림을 제공하도록 개선.

| 구분 | 변경 내용 |
|------|----------|
| 전제 조건 2-tier | REQUIRED (차단) / RECOMMENDED (경고만) 분리 |
| 조건 완화 | `industry`, `deal_structure`, `estimated_deal_value` → RECOMMENDED로 격하 |
| 자동 전환 알림 | `can_advance`가 true가 되면 toast 알림 + 원클릭 진행 버튼 |
| UI 구분 | 필수 조건은 빨간 원, 권장 조건은 노란 원 + "(권장)" 라벨 |

## 수정 파일 (7개)

| 파일 | 작업 | 라인 변경 |
|------|------|----------|
| `deal-mgmt/app/schemas/workflow.py` | `PrerequisiteLevel` enum, `required_met`, `has_warnings` 필드 추가 | +15 |
| `deal-mgmt/app/services/workflow_engine.py` | 3-tuple 전제 조건, `required_met` 기준 전환 | ~40 |
| `deal-mgmt/tests/test_workflow.py` | 기존 테스트 수정 + 새 테스트 4개 추가 | +80 |
| `amic-platform/src/modules/ma/types/workflow.ts` | FE 타입 확장 (`PrerequisiteLevel`, `level`, `required_met`, `has_warnings`) | +5 |
| `amic-platform/src/modules/ma/hooks/useTransactions.ts` | `useAutoAdvanceNotification` 훅 추가 | +46 |
| `amic-platform/src/modules/ma/components/PhaseActionPanel.tsx` | 2-tier UI 구분 (REQUIRED/RECOMMENDED 분리 표시) | ~50 |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx` | 알림 훅 연결 + 경고 배지 | +10 |

## 백엔드 변경 상세

### 1. 스키마 확장 (`deal-mgmt/app/schemas/workflow.py`)

```python
class PrerequisiteLevel(str, Enum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"

class PhasePrerequisite(BaseModel):
    field: str
    label: str
    satisfied: bool
    level: PrerequisiteLevel = PrerequisiteLevel.REQUIRED

class PhaseCompletionStatus(BaseModel):
    # ... 기존 필드 유지
    required_met: bool = True      # REQUIRED만 충족 여부
    has_warnings: bool = False     # RECOMMENDED 미충족 존재 여부
```

### 2. 워크플로우 엔진 (`deal-mgmt/app/services/workflow_engine.py`)

**전제 조건 2-tuple → 3-tuple 변환**:
```python
_PHASE_PREREQUISITES = {
    PREPARATION: [
        ("client_name", "클라이언트 정보", REQUIRED),
        ("lead_advisor_email", "리드 어드바이저", REQUIRED),
    ],
    MARKETING: [
        ("target_company_name", "대상 기업 정보", REQUIRED),
        ("industry", "산업 분류", RECOMMENDED),        # 완화
    ],
    BIDDING_DD: [
        ("deal_structure", "딜 구조", RECOMMENDED),     # 완화
    ],
    NEGOTIATION: [
        ("estimated_deal_value", "예상 거래 금액", RECOMMENDED),  # 완화
    ],
}
```

**완화 근거**:
- `industry`: 마케팅 시작 후 산업 분류 확정 가능
- `deal_structure`: 입찰 과정에서 딜 구조 확정 빈번
- `estimated_deal_value`: 가격은 협상 단계에서 구체화

**전환 로직**: `advance_phase()`와 `request_phase_approval()`에서 `completion.all_met` → `completion.required_met`로 변경.

### 3. 테스트 (`deal-mgmt/tests/test_workflow.py`)

16/16 전체 통과. 추가된 테스트:
- `test_phase_status_shows_levels`: phase-status 응답에 `level`, `required_met`, `has_warnings` 포함 확인
- `test_full_prerequisites_all_met`: 모든 조건 충족 시 `all_met=True`, `has_warnings=False`
- `test_advance_with_recommended_warnings`: RECOMMENDED 미충족 시에도 전진 성공
- `test_phase_status_has_warnings_when_recommended_unmet`: RECOMMENDED 미충족 시 `has_warnings=True`

**참고**: REQUIRED 실패 테스트는 `TransactionCreate` 스키마가 `client_name: Field(..., min_length=1)`로 이미 API 레벨에서 차단하므로 별도 워크플로우 테스트 불필요.

## 프론트엔드 변경 상세

### 4. 타입 확장 (`workflow.ts`)

```typescript
export type PrerequisiteLevel = "REQUIRED" | "RECOMMENDED";
// PhasePrerequisite에 level 추가, PhaseCompletionStatus에 required_met, has_warnings 추가
```

### 5. 자동 전환 알림 훅 (`useTransactions.ts`)

`useAutoAdvanceNotification(txnId)`:
- `useRef`로 이전 `can_advance` 상태 추적
- `false → true` 전환 시에만 toast 알림 1회 발생
- `has_warnings` 존재 시 `toast.info`, 없으면 `toast.success`
- sonner toast의 `action` 옵션으로 원클릭 진행 버튼
- `advanceRef = useRef(advancePhase)` 패턴으로 의존성 배열 최적화

### 6. PhaseActionPanel UI (`PhaseActionPanel.tsx`)

- 프로그레스 바: REQUIRED 충족률 기준
- REQUIRED 미충족: 빨간 `Circle` (text-negative)
- RECOMMENDED 미충족: 노란 `Circle` (text-caution) + "(권장)" 라벨
- 섹션 분리: REQUIRED 먼저, "권장 사항" 구분 후 RECOMMENDED

### 7. 워크스페이스 연결 (`TransactionWorkspacePage.tsx`)

- `useAutoAdvanceNotification(id!)` 호출 추가
- "다음 단계로" 버튼 옆 경고 배지: `⚠ 권장 항목 미완료` (text-caution)

## 코드 리뷰 결과

### 발견 및 수정 완료 (2건)

| ID | 심각도 | 이슈 | 수정 |
|----|--------|------|------|
| W-1 | Medium | `text-warning` CSS 클래스 미존재 (tailwind config에 없음) | `text-caution`으로 전체 교체 |
| W-2 | Medium | `useEffect` 의존성 배열에 `advancePhase` 객체 → 불필요한 재실행 | `useRef` 패턴으로 안정화 |

### 참고 사항 (수정 불필요)

| ID | 설명 |
|----|------|
| S-1 | PhaseActionPanel early return 위치 최적화 가능 (성능 영향 미미, 선택사항) |
| S-2 | `_collect_prerequisites()`에서 다음 단계 조건 평가하는 이유 주석 보강 권장 |

## 검증

- **백엔드 테스트**: `pytest tests/test_workflow.py` — 16/16 PASSED
- **프론트엔드 타입**: `npx tsc --noEmit` — 0 errors
- **CSS 토큰**: tailwind.config.js에서 `caution: "#EF6C00"` 존재 확인
