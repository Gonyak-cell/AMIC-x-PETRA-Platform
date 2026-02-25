# VCP Self-Challenge 업데이트 보고서

> **작성일**: 2026-02-23 12:12:00
> **변경 유형**: 코드 리뷰 시스템 개선 (Claude Code Security 인사이트 적용)
> **프로토콜 버전**: Verified Claim Protocol v1.1 → **v1.2**

---

## 배경

Anthropic의 Claude Code Security 발표([링크](https://www.anthropic.com/news/claude-code-security))에서 두 가지 핵심 기법을 기존 코드 리뷰 시스템에 적용:

1. **다단계 자기 검증**: 에이전트가 이슈를 발견한 직후 스스로 "적대적 재검토자" 역할로 동일 코드를 다시 검토 → 허위 양성 사전 제거
2. **심각도 + 신뢰도 이중 등급**: 두 차원을 `[Critical/HIGH]` 형태로 이슈 헤더에 명시적 표시

### 기존 시스템의 갭

| 갭 | 문제 |
|----|------|
| `review-verifier.md` 파일 없음 | Phase 2 Cross-Verification이 존재하지 않는 에이전트를 참조 |
| VCP에 "발견 후 재검토" 단계 없음 | 자기 검증이 초기 분석 중에만 수행 (적대적 재검토 부재) |
| 신뢰도 등급 헤더에 묻혀 있음 | 이슈 목록 스캔 시 신뢰도 즉시 파악 불가 |

---

## 변경 내역

### 1. VCP — 3.5단계 Self-Challenge 추가 (`verified-claim-protocol.md`)

#### 변경 전
```
5단계 검증 프로토콜:
1단계 → 2단계 → 3단계 → 4단계 → 5단계
```

#### 변경 후
```
6단계 검증 프로토콜 (3.5단계 포함):
1단계 → 2단계 → 3단계 → [3.5단계: Self-Challenge] → 4단계 → 5단계
```

#### Self-Challenge 체크리스트 (SC-1 ~ SC-6)

| 항목 | 질문 | 기각 조건 |
|------|------|---------|
| **SC-1** 실행 경로 | 실제로 도달 가능한 코드 경로인가? | dead code, disabled → REJECT |
| **SC-2** 의존성 부재 | Grep으로 재확인했는가? barrel export 확인? | 발견 시 → REJECT |
| **SC-3** 라이브러리 동작 | 프레임워크가 내부 처리하는 기능을 "누락"으로 오판? | 오판 시 → REJECT |
| **SC-4** 백엔드 계약 | 스키마 불일치를 백엔드 코드로 확인했는가? | 가정만 → REJECT |
| **SC-5** 의도된 패턴 | 코드베이스 전체에서 동일 패턴 Grep 확인? | 의도된 패턴 → REJECT |
| **SC-6** 수정안 안전성 | 수정안이 타입 에러/런타임 오류 유발 안 하는가? | 재작성 필요 |

**신뢰도 자동 하향**:
- SC △ 1개 → 신뢰도 MEDIUM
- SC △ 2개 이상 → 신뢰도 LOW

#### 거부 규칙 확장

```
기존: "3단계에서 가설이 반증되면 보고하지 않는다"
변경: "3단계 또는 3.5단계(Self-Challenge)에서 가설이 반증되면 보고하지 않는다"
```

새 거부 카테고리 추가: **Self-Challenge 기각** (SC-1~SC-5 중 ✗ 판정)

---

### 2. 이슈 헤더 형식 변경 (`verified-claim-protocol.md`)

#### 변경 전
```
### [C-S1] XSS 취약점 — Critical — Confidence: HIGH — Priority: P0
```

#### 변경 후
```
### [C-S1] XSS 취약점 — [Critical/HIGH] — Priority: P0
```

신뢰도 하향 예시:
```
### [C-S2] 인증 우회 — [Critical/MEDIUM ⚠️] — Priority: P1
### [M-A1] 타입 불일치 — [Major/LOW ⚠️⚠️] — Priority: P2
```

**검증 추적 섹션에 Self-Challenge 기재란 추가**:
```
5. ✓ Self-Challenge: SC-1(✓) SC-2(✓) SC-3(△) SC-4(△) SC-5(✓) SC-6(✓) → PASS (신뢰도 MEDIUM 하향)
```

---

### 3. review-verifier.md 에이전트 신규 생성 (`agents/review-verifier.md`)

**경로**: `amic-platform/.claude/agents/review-verifier.md`

Phase 2 Cross-Verification에서 참조되던 **누락 에이전트**를 구현.

#### 4단계 검증 절차

1. **위치 독립 확인** — Phase 1과 독립적으로 Glob 재실행
2. **코드 독립 읽기** — Phase 1의 코드 스니펫과 실제 코드 비교
3. **컨텍스트 확장 검증** — import, 타입 정의, 백엔드 엔드포인트 추가 확인
4. **Self-Challenge** — VCP 3.5단계 SC-1~SC-6 적용

#### 5단계 판정

| 판정 | 조치 |
|------|------|
| CONFIRMED | 유지 + **+15 보너스** |
| FALSE_POSITIVE | 제거 + FP 6종 분류 |
| PARTIAL | 심각도/설명 조정 |
| DESIGN_RISK | 기술 부채 재분류 |
| LINE_MISMATCH | 위치 수정 후 유지 |

---

### 4. review-orchestrate 보강 (`review-orchestrate/SKILL.md`)

#### Phase 1 에이전트 프롬프트

```diff
  모든 이슈에 대해 반드시:
  1. Read로 실제 코드를 확인한 뒤 클레임
  2. 증거(실제 코드 스니펫) 첨부
  3. 신뢰도 점수 (HIGH/MEDIUM/LOW) 부여
  4. 가설이 반증되면 보고하지 않기
+ 5. 3.5단계 Self-Challenge: 이슈 초안 완성 후 SC-1~SC-6 적용
+    - SC-1~SC-5 중 하나라도 ✗ → 이슈 기각
+    - △ 항목 수에 따라 신뢰도 자동 하향

+ 이슈 헤더 형식: [{ID}] {제목} — [{심각도}/{신뢰도}] — Priority: {P0/P1/P2/P3}
```

#### Phase 2 호출 프롬프트

```diff
  각 이슈에 대해:
+ 1. Phase 1 에이전트와 독립적으로 Glob + Read로 코드를 직접 확인
+ 2. VCP Self-Challenge(3.5단계) SC-1~SC-6 체크리스트 각 이슈에 적용
  3. 5단계 판정: CONFIRMED / FALSE_POSITIVE / PARTIAL / DESIGN_RISK / LINE_MISMATCH
  4. 허위 양성은 FP 6종 원인 분류(FP-IMPL/FP-HALLUC/FP-LINE/FP-LOGIC/FP-CTX/FP-SEV) 필수
```

#### Priority Matrix 형식

```diff
- 1. [ID]: one-line summary — file — Confidence: HIGH (점수: N)
+ 1. [ID] [Critical/HIGH]: one-line summary — file (점수: N)
+ 2. [ID] [Critical/MEDIUM ⚠️]: one-line summary — file (점수: N, 신뢰도 하향됨)
```

---

## 변경 파일 목록

| 파일 | 변경 유형 | 핵심 변경 |
|------|---------|---------|
| `amic-platform/.claude/rules/verified-claim-protocol.md` | 수정 | 3.5단계 Self-Challenge, 헤더 형식, 거부 사유 |
| `amic-platform/.claude/agents/review-verifier.md` | **신규 생성** | Phase 2 교차 검증 에이전트 |
| `amic-platform/.claude/skills/review-orchestrate/SKILL.md` | 수정 | Phase 1/2 프롬프트 보강, Priority Matrix 형식, frontmatter 오류 수정 |

---

## 예상 효과

| 지표 | 개선 전 | 개선 후 (예상) |
|------|--------|------------|
| 허위 양성 발생율 | 기준값 | SC 기각으로 15~30% 추가 감소 |
| Phase 2 작동 여부 | 에이전트 파일 없음 → 미작동 | review-verifier.md 생성 → 작동 |
| 이슈 헤더 가독성 | Confidence: HIGH 텍스트 | `[Critical/HIGH]` 즉시 파악 |
| 신뢰도 하향 추적 | ⚠️ 주석만 | 헤더 + 검증 추적 + 거부 사유 통합 |

---

## VCP 버전 이력

| 버전 | 날짜 | 주요 변경 |
|------|------|---------|
| v1.0 | 2026-02-13 | 최초 5단계 검증 프로토콜 |
| v1.1 | 2026-02-16 | 신뢰도 가중 우선순위 (P0~P3 공식), 거부 사유 6분류 |
| **v1.2** | **2026-02-23** | **3.5단계 Self-Challenge, `[심각도/신뢰도]` 헤더, review-verifier 에이전트 생성** |
