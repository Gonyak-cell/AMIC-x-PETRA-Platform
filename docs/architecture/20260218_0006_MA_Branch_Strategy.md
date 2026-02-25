# MA 워크플로우 브랜치 전략

**작성일**: 2026-02-18 00:05
**백업 태그**: `v0.9-pre-ma-workflow` → 커밋 `50da757`
**작업 브랜치**: `feat/ma-workflow`
**관련 문서**: `docs/architecture/20260217_2304_MA_Workflow_Implementation_Plan.md`

---

## 현재 상태

- **현재 브랜치**: `feat/ma-workflow` (MA 워크플로우 전용)
- **master 브랜치**: MA 변경 이전 안정 버전 보존
- **백업 태그**: `v0.9-pre-ma-workflow` — MA 작업 시작 직전 스냅샷

---

## 작업 방식

| 작업 유형 | 브랜치 | 비고 |
|:---|:---|:---|
| MA 워크플로우 관련 작업 | `feat/ma-workflow` | Phase 0~4 전체 |
| 기존 기능 버그픽스/유지보수 | `master` | FDD, KIIS, IM, 공통 UI |

---

## 주요 명령어

### 브랜치 전환

```bash
# MA 작업하러 가기
git checkout feat/ma-workflow

# 기존 기능 유지보수하러 가기
git checkout master
```

### 복원이 필요할 때

```bash
git checkout master          # MA 변경 전 상태로 복원
git tag -l                   # v0.9-pre-ma-workflow 태그 확인
```

### MA 작업 완료 후 병합

```bash
git checkout master
git merge feat/ma-workflow   # master에 병합
```

### 태그로 특정 시점 확인

```bash
git show v0.9-pre-ma-workflow --no-patch   # 태그 상세 정보
git diff v0.9-pre-ma-workflow..HEAD        # 태그 이후 변경사항
```

---

## 주의사항

- MA 워크플로우는 아키텍처 전체 변경 (`deal-mgmt` 서비스 신설, FDD/IM 통합)이므로 반드시 별도 브랜치에서 작업
- master에서 긴급 수정이 필요한 경우, 작업 후 `feat/ma-workflow`에도 rebase 또는 merge 필요
- 병합 전 반드시 `tsc --noEmit` + `vite build` 검증
