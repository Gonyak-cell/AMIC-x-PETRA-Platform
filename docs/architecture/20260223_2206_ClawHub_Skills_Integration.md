# ClawHub / Claude Skills 통합 작업 보고서

> 작성: 2026-02-23 22:06
> 세션: Session 34
> 브랜치: `feat/ma-workflow`

---

## 1. 배경 및 목적

ClawHub.ai 스킬 마켓플레이스에서 AMIC x PETRA Platform에 도움이 될 수 있는 스킬, 규칙, 훅을 조사하고, 프로젝트 기술 스택에 맞게 커스터마이즈하여 적용.

**조사 대상**: ClawHub.ai, awesome-claude-skills (travisvn), awesome-openclaw-skills (VoltAgent), software-dev-ai-claude-toolkit (Ashfaqbs), obra/superpowers, Trail of Bits Security Skills, Pulumi Blog DevOps Skills

---

## 2. 적용 완료 내역

### 2-1. Rules 5개 추가 (`amic-platform/.claude/rules/`)

| 파일 | 내용 | 출처 | 라인 수 |
|------|------|------|---------|
| `python-backend.md` | FastAPI/Pydantic v2/SQLAlchemy 2.0 규칙, 모듈별 디렉토리 구조 | software-dev-ai-claude-toolkit | 62 |
| `database-patterns.md` | PostgreSQL + Alembic 마이그레이션 패턴, 쿼리 최적화 | software-dev-ai-claude-toolkit | 31 |
| `testing-standards.md` | pytest/Vitest/Playwright 테스트 표준, TDD 워크플로우 | toolkit + obra/superpowers | 40 |
| `security-checklist.md` | OWASP 보안 체크리스트, SEC-001 참조, Trail of Bits 참고 | toolkit + Trail of Bits | 42 |
| `infra-docker.md` | Docker/docker-compose/nginx 규칙, 모노레포 서비스 구성 | software-dev-ai-claude-toolkit | 53 |

### 2-2. Skills 2개 추가 (`amic-platform/.claude/skills/`)

| 스킬 | 내용 | 출처 | 라인 수 |
|------|------|------|---------|
| `systematic-debugging/SKILL.md` | 4단계 근본 원인 분석 디버깅 (근본 원인 조사 → 패턴 분석 → 가설 테스트 → 구현) | obra/superpowers | 109 |
| `tdd/SKILL.md` | RED-GREEN-IMPROVE TDD 사이클, pytest/Vitest 예시 포함 | obra/superpowers | 153 |

### 2-3. Hooks 2개 추가 (`~/.claude/settings.json`)

| 훅 | 트리거 | 동작 |
|----|--------|------|
| Python print() 경고 | `.py` 파일 Edit 시 | `print()` 발견 시 `logging` 모듈 사용 권고 |
| JS/TS console.log 경고 | `.js/.jsx/.ts/.tsx` 파일 Edit 시 | `console.log` 발견 시 커밋 전 제거 권고 |

---

## 3. 자체 검증 결과

### 검증 방법
- 생성된 7개 파일 + 1개 설정 변경을 전부 Read
- Explore 에이전트로 코드베이스 실제 구조/파일/설정 대조
- 각 주장(claim)에 대해 True/False 판정

### 발견 및 수정된 이슈

| # | 파일 | 문제 | 심각도 | 상태 |
|---|------|------|--------|------|
| ISSUE-1 | `infra-docker.md` L21-30 | 서비스 이름 오류 (`fdd-backend` → 실제 `fdd-api`), 공유 postgres → 실제 모듈별 독립 DB | Medium | **수정 완료** |
| ISSUE-2 | `python-backend.md` L20-31 | 단일 구조 일괄 적용 → FDD는 `app/api/`, IM은 `src/api/routes/` | Medium | **수정 완료** |

### 검증 통과 항목 (6/8)

| # | 검증 항목 | 결과 |
|---|----------|------|
| 1 | SEC-001 httpOnly 쿠키 참조 | TRUE — `token-storage.ts` 삭제, `withCredentials: true` 2곳 확인 |
| 2 | Alembic 마이그레이션 패턴 | TRUE — 10개 파일 전부 `{번호}_{설명}.py` 일치 |
| 3 | asyncpg 사용 표현 | TRUE — FDD만 동기, 나머지 asyncpg |
| 4 | systematic-debugging 원본 대조 | TRUE — 4단계 프로세스 충실 반영 |
| 5 | TDD 원본 대조 | TRUE — RED-GREEN-IMPROVE 정확 |
| 6 | Hooks 문법/Windows 호환 | TRUE — node -e, Windows 경로 호환 |

**최종 정확도**: 100% (수정 후)

---

## 4. 조사 결과 요약 — 추가 도입 후보

### 즉시 활용 가능 (Anthropic 공식, 내장)

| Skill | 용도 | 프로젝트 적용 |
|-------|------|--------------|
| `pptx` | PowerPoint 생성/편집/분석 | deal-mgmt pptx-service, IM TM/DM |
| `xlsx` | Excel 처리 | FDD 재무 데이터, KIIS 펀드 데이터 |
| `docx` | Word 문서 처리 | Legal Documents, LDD Reports |
| `pdf` | PDF 추출/병합/분할 | 계약서 분석, 보고서 변환 |
| `webapp-testing` | Playwright UI 테스트 | E2E 검증 강화 |
| `frontend-design` | React + Tailwind 디자인 | UI 컴포넌트 개선 |

### 선택적 도입 후보

| 항목 | 출처 | 용도 |
|------|------|------|
| Trail of Bits Security Skills | trailofbits/skills | CodeQL/Semgrep 정적 분석 |
| monitoring-expert | jeffallan/claude-skills | 구조화된 로깅, 메트릭 |
| incident-runbook-templates | wshobson/agents | 인시던트 대응 런북 |
| Proactive Agent | ClawHub | 자율적 에이전트 프레임워크 |
| Skill_Seekers | yusufkaraaslan | 문서 → 스킬 변환 |

### 보안 경고

> **ClawHub 공급망 공격 사건** (2026-01-27 ~ 02-02): 341개 악성 스킬 발견, 1,184개 오염된 패키지. ClawHub에서 직접 설치하지 말고 **GitHub 원본 저장소 확인 후 SKILL.md 내용만 참조/복사** 권장.

---

## 5. 변경된 파일 목록

```
신규:
  amic-platform/.claude/rules/python-backend.md
  amic-platform/.claude/rules/database-patterns.md
  amic-platform/.claude/rules/testing-standards.md
  amic-platform/.claude/rules/security-checklist.md
  amic-platform/.claude/rules/infra-docker.md
  amic-platform/.claude/skills/systematic-debugging/SKILL.md
  amic-platform/.claude/skills/tdd/SKILL.md

수정:
  ~/.claude/settings.json  (hooks 추가)
```

---

## 6. 참조 링크

- [awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills)
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills)
- [software-dev-ai-claude-toolkit](https://github.com/Ashfaqbs/software-dev-ai-claude-toolkit)
- [obra/superpowers](https://github.com/obra/superpowers)
- [Trail of Bits Security Skills](https://github.com/trailofbits/skills)
- [Top 8 Claude Skills for DevOps (Pulumi)](https://www.pulumi.com/blog/top-8-claude-skills-devops-2026/)
- [ClawHub](https://clawhub.ai/skills?sort=downloads)
