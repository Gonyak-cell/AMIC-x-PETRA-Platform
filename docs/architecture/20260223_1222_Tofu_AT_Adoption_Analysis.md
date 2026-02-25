# Tofu-AT (Agent Team) 도입 장단점 분석

> 작성일: 2026-02-23 12:22
> 대상 프로젝트: AMIC x PETRA Platform
> 원본 시스템: github.com/treylom/tofu-at

---

## 개요

Tofu-AT는 Claude Code Agent Teams를 기반으로 에이전트 팀을 설계·실행·모니터링하는 스킬 시스템이다.
이 문서는 AMIC x PETRA Platform에 Tofu-AT를 도입할 경우의 장단점을 분석한다.

---

## 프로젝트 현황 요약

| 항목 | 현황 |
|------|------|
| 규모 | 모노레포 5개 모듈, ~18K LOC (amic-platform 17K + 백엔드 4개 1K) |
| 기존 에이전트 인프라 | `review-orchestrate` 6단계 병렬 파이프라인 완성 |
| 검증 프로토콜 | VCP v1.1 (신뢰도 가중 우선순위), Phase 0B Review Gates |
| 배포 준비도 | 80% (코드 완성, 배포 인프라 대기) |
| 환경 | Windows 11, Node.js 설치됨, tmux 없음 |

---

## 장점

### 1. 완전히 새로운 워크플로우 설계 자동화
현재 `review-orchestrate`는 코드 리뷰에 특화되어 있다.
**MA Phase 3 AI 계약 분석**, **Docs 모듈 PPT 생성**, **4개 백엔드 동시 배포 검증** 같은
전혀 다른 유형의 에이전트 팀을 설계할 때 `/tofu-at scan`이 유용하다.

### 2. Agent Office 모니터링
`review-orchestrate`가 현재 6단계 파이프라인을 실행할 때 터미널 출력만으로 추적한다.
에이전트 상태를 `localhost:3747`에서 시각적으로 확인하면 디버깅이 편해진다.

### 3. Registry로 반복 팀 재사용
MA 워크플로우처럼 반복적인 대형 작업에서 `/tofu-at catalog {id}`로 저장하고
`/tofu-at spawn {id}`로 재실행하는 패턴이 유용하다.

---

## 단점

### 1. 기존 인프라와 핵심 기능이 직접 충돌 ⚠️
`review-orchestrate`는 이미 에이전트 병렬 실행, 의존성 관리, 오케스트레이션을 완전히 구현한다.
Tofu-AT의 핵심 가치인 "에이전트 팀 설계·실행"이 **이미 있다**.

### 2. VCP v1.1과 충돌 위험 ⚠️
Tofu-AT의 스폰 템플릿은 이 프로젝트의 `verified-claim-protocol.md`(신뢰도 가중 우선순위),
`review-gates.md`(Phase 0B 검증)를 전혀 모른다.
Tofu-AT가 생성한 에이전트가 VCP 없이 동작하면 기존 리뷰 품질 보장 체계가 무력화된다.

### 3. 금융 도메인 특화 지식 부재
FDD, KIIS, IM, MA 같은 금융 도메인에 특화된 에이전트를
Tofu-AT의 137개 범용 페르소나 템플릿(Frontend, Storage, QA 등)으로 자동 생성하기 어렵다.

### 4. 모노레포 구조 미인식
4개 백엔드 + 프론트엔드 모노레포 구조에서 `/tofu-at scan`이
`monorepo-only.md` 규칙(모노레포 전용 경로)을 자동 적용하지 않는다.

### 5. 프로젝트 루트 오염
`.team-os/`, `agent-office/`가 금융 플랫폼 루트에 생긴다.
Docker 볼륨 마운트, CI/CD 파이프라인, 팀원 협업에서 노이즈가 된다.

### 6. 배포 준비 단계에서 실험적 기능 추가는 리스크
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`은 Research Preview 단계다.
현재 배포 준비 80% 시점에서 불안정 요소 추가는 적절하지 않다.

### 7. Windows auto 모드 = 기존 Task 도구와 동일
tmux 없이 auto 모드는 이미 `review-orchestrate`에서 사용 중인
Task 도구 기반 병렬 실행과 차이가 없다.

---

## 실질적 이득 평가

| 시나리오 | 이득 | 이유 |
|---------|------|------|
| 코드 리뷰 에이전트 팀 | ❌ | 이미 6단계 파이프라인 완성 |
| MA Phase 3 AI 에이전트 설계 | ✅ | 완전히 새로운 워크플로우 |
| Docs 모듈 PPT 생성 에이전트 | ✅ | 새 도메인 |
| 4개 백엔드 배포 검증 팀 | △ | 유용하지만 직접 스킬로 만드는 게 나을 수 있음 |
| 기존 스킬 Agent Teams 전환 | ❌ | VCP 충돌 위험 |
| 에이전트 상태 모니터링 | △ | 유용하지만 Node.js 서버 상시 실행 부담 |

---

## `.claude` 폴더 위치 결정

프로젝트에 `.claude` 폴더가 두 곳 존재한다:

| 경로 | 용도 |
|------|------|
| `./.claude` (루트) | 모노레포 전체 설정 (git-workflow.md 등) |
| `./amic-platform/.claude` | 프론트엔드 전용 설정 (skills, rules, hooks 등) |

Tofu-AT 설치 시:
- 스킬 3개 + 커맨드 → `amic-platform/.claude/`
- `.team-os/`, `agent-office/` → 모노레포 루트 (불가피)

---

## 권고

**지금 당장 전체 설치는 권장하지 않는다.**

**최소 설치 (권장)**: 스킬 3개 + 커맨드 파일만 (`.team-os/`, `agent-office/` 제외)
→ `/tofu-at scan` 기능만 활용, 나머지는 기존 인프라 유지

**전체 설치 적합 시점**:
- MA Phase 3처럼 LLM/외부 API 연동 등 완전히 새 워크플로우 설계 시
- WSL + tmux 환경 구성 후 (진짜 멀티 세션 장점 활용 시)
- 배포 완료 후 안정화 단계에서

---

## 참고

- 원본: https://github.com/treylom/tofu-at
- 기존 인프라: `amic-platform/.claude/skills/review-orchestrate/SKILL.md`
- VCP 프로토콜: `amic-platform/.claude/rules/verified-claim-protocol.md`
- Review Gates: `amic-platform/.claude/rules/review-gates.md`
