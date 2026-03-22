# 2026-03-22 Platform UI Consistency Audit

## 정의

- `HeaderHierarchyMismatch`
  - 같은 업무 단위의 카드/섹션인데 헤더 구조, 제목 스타일, 강조 방식이 달라 상하위 관계가 달라 보이는 상태
- `DuplicatePrimaryAction`
  - 이미 페이지 상단 또는 카드 헤더에 상시 노출된 1차 액션이 빈 상태 안에 동일한 액션으로 한 번 더 반복되는 상태
- `ActionPlacementMismatch`
  - 같은 종류의 생성/추가 액션이 어떤 섹션은 헤더 우측, 어떤 섹션은 본문 중앙, 어떤 섹션은 별도 레일에 있어 사용 위치가 흔들리는 상태
- `PeerButtonTreatmentMismatch`
  - 같은 계층의 헤더 액션인데 버튼 크기, variant, 아이콘 처리, 텍스트 밀도가 달라 보이는 상태
- `InlineTextIntegrityMismatch`
  - 생성 폼은 검증하지만 인라인 수정은 검증하지 않아 같은 데이터가 화면마다 다른 품질 기준으로 저장되는 상태
- `LocalLocaleMismatch`
  - 한 화면 안에서 같은 계층의 섹션/액션이 한국어와 영어를 혼용해 보이는 상태

## 이번 정리 범위

- M&A 워크스페이스
  - `Engagement`, `NDA`, `Bids`, `Closing`, `DD Checklist`, `Contracts`, `PMI`, `Earnout`, `Deal Client`, `Transaction List`
- FDD
  - `Deal List`, `Definition`, `Issues`, `Mapping`, `QoE`, `Net Debt`
- Docs / IM / Admin
  - `DD Report List`, `Category Documents`, `Document List`, `User Management`
- Transaction text integrity
  - 생성 폼, 수동 딜 셋업, Overview 인라인 수정, API schema, create/update API tests

## 적용 원칙

- 생성/추가의 1차 액션은 가능한 한 카드 헤더 또는 페이지 헤더에 고정한다.
- 빈 상태는 설명과 안내에 집중하고, 동일한 1차 액션을 중복 배치하지 않는다.
- 같은 계층의 카드 헤더 액션은 `ghost + sm` 조합을 기본값으로 맞춘다.
- 거래명/대상기업/클라이언트처럼 한글 입력이 자주 일어나는 핵심 텍스트는 생성과 수정 모두 동일한 검증 규칙을 사용한다.
- 한 화면 안에서 같은 계층의 섹션 제목은 가능하면 동일한 언어와 헤더 패턴을 사용한다.

## 반영 결과

- `HeaderHierarchyMismatch`
  - `EngagementTab`의 `워킹 그룹` 섹션을 `수임계약`과 동일한 카드 헤더 패턴으로 통일
- `DuplicatePrimaryAction`
  - 워크스페이스/리스트/문서 관리 화면에서 헤더 또는 페이지 상단에 이미 있던 생성 액션을 빈 상태에서 제거
- `ActionPlacementMismatch`
  - `ContractsTab`에 `계약서 추가`를 헤더 우측 상시 액션으로 승격
- `PeerButtonTreatmentMismatch`
  - `NDA`, `Bids`, `Closing`, `PMI`, `Earnout`, `Deal Client`, `Contracts` 헤더 액션을 소형 고스트 버튼 패턴으로 정리
- `InlineTextIntegrityMismatch`
  - API schema와 프런트 유틸을 동일 규칙으로 맞추고, Overview 인라인 수정도 동일 검증을 통과해야 저장되도록 변경
- `LocalLocaleMismatch`
  - `EngagementTab`의 `Working Group` 표기를 `워킹 그룹`으로 통일

## 검토 후 유지한 예외

- `VdrPage`
  - 상단 액션은 `Run Auto Analysis`, 빈 상태 액션은 `Initialize VDR`로 목적이 달라 유지
- `ChecklistReviewPage`
  - 체크리스트가 아직 없을 때는 상단 고정 액션이 없고 빈 상태 CTA만 존재하므로 유지
- `ReportPage`
  - 미리보기는 카드 내부 맥락 액션이라 빈 상태 CTA 유지
- `StudioHomePage`
  - 상단은 문서 생성, 빈 상태는 거래 생성으로 목적이 달라 유지
- `ChecklistDetailPage`
  - 메시지형 상태 액션을 동적으로 주입하는 구조라 일괄 제거 대상에서 제외

## 검증 절차

1. 거래 생성 폼에서 `NX게임즈`, `최일곤`을 입력해 생성 후 즉시 다시 조회한다.
2. 거래 Overview 인라인 입력에서 `???`, `NX3???`, `�`가 포함된 값을 입력해 저장이 차단되는지 확인한다.
3. 워크스페이스 카드 헤더의 생성 액션이 모두 헤더 우측에 고정되어 있고, 빈 상태 본문에는 동일 액션이 중복되지 않는지 확인한다.
4. `rg -n "actionLabel=" amic-platform/src -g "*.tsx"` 결과가 예외로 문서화한 파일만 남는지 확인한다.
