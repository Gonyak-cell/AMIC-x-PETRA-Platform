# MA 파이프라인 UI 수정

> 작성: 2026-02-25 09:40

## 수정 내역

### 1. 파이프라인 테이블 모서리 스타일 통일
- **파일**: `amic-platform/src/modules/ma/pages/TransactionListPage.tsx:272`
- **문제**: DataTable이 Card 안에서 이중 border + rounded corner 적용 → UserManagementPage와 모서리 불일치
- **원인**: DataTable에 `borderless` prop 미전달 → `border border-gray-border rounded-dr` 추가됨
- **수정**: `borderless` prop 추가 → Card의 rounded corner만 사용

### 2. 마케팅 로그 버튼 텍스트 변경
- **파일**: `amic-platform/src/modules/ma/components/meetings/MeetingLogsTab.tsx:126`
- **변경**: `{phaseLabel} 미팅 추가` → `로그 추가`
- **효과**: 마케팅/협상 구분 없이 동일한 텍스트로 통일

### 3. Button 컴포넌트 줄바꿈 방지
- **파일**: `amic-platform/src/components/ui/Button.tsx:93`
- **문제**: 버튼 텍스트가 2줄로 줄바꿈됨
- **수정**: `whitespace-nowrap` 클래스 추가 → 모든 버튼 텍스트 한 줄 유지

### 4. 이견 등록 버튼 사이즈 통일
- **파일**: `amic-platform/src/modules/ma/components/meetings/NegotiationIssuePanel.tsx:79`
- **변경**: `size="sm"` 제거 → 기본 `md` 적용 (로그 추가 버튼과 동일 사이즈)
