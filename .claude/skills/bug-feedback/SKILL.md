---
name: bug-feedback
description: "에러 로그 분석 및 지시 효율성 피드백 통합 스킬"
---

# Bug Feedback Skill

에러/버그 로그와 사용자 지시 로그를 분석하여 반복 패턴 리포트와 효율성 피드백을 제공합니다.

## 데이터 소스

| 파일 | 역할 | 생성 방식 |
|------|------|----------|
| `logs/errors.jsonl` | 도구 실행 에러 원시 로그 | PostToolUse/PostToolUseFailure 훅 자동 기록 |
| `logs/prompts.jsonl` | 사용자 지시 원시 로그 | UserPromptSubmit 훅 자동 기록 |
| `knowledge/bug-patterns.md` | 에러 패턴 분석 결과 | analyze_bugs.py 실행 시 재생성 |
| `knowledge/prompt-patterns.md` | 지시 패턴 분석 결과 | analyze_prompts.py 실행 시 재생성 |

## 분석 스크립트

### 에러 패턴 분석
```bash
python .claude/skills/bug-feedback/scripts/analyze_bugs.py --days 30
```
- `logs/errors.jsonl` 읽기 → 에러 메시지 클러스터링 → 반복 패턴 추출
- `knowledge/bug-patterns.md` 재생성
- memory 폴더에 자동 복사 (세션 자동 참조용)
- 30일 이전 로그 자동 아카이브

### 지시 패턴 분석
```bash
python .claude/skills/bug-feedback/scripts/analyze_prompts.py --days 30
```
- `logs/prompts.jsonl` 읽기 → 카테고리 분포 + 세션 흐름 분석
- implement→fix, fix→fix 등 비효율 패턴 감지
- 효율성 개선 제안 자동 생성
- `knowledge/prompt-patterns.md` 재생성

## 관련 커맨드

- `/bug-report [days]` — 에러 패턴 리포트 생성
- `/prompt-feedback [days]` — 지시 효율성 피드백 제공
