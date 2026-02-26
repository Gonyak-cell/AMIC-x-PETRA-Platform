# Code Freeze (전체 소스코드 동결)

> **핵심**: 현재 코드베이스는 프로덕션 안정성이 검증된 상태이다.
> **모든 소스코드 파일 수정은 사용자의 명시적 승인 없이 절대 금지한다.**

## 적용 시점

**모든 작업에서 자동 적용.**
기능 개발, 리팩토링, 버그 수정, 개선, 정리, 포맷팅 등 어떤 목적이든 동일하게 적용된다.

## 보호 범위

모든 소스코드 파일:
- `*.py` — Python 백엔드 (FDD, KIIS, IM, deal-mgmt)
- `*.ts`, `*.tsx` — TypeScript 프론트엔드 (amic-platform)
- `*.yml`, `*.yaml` — Docker, CI/CD, 설정
- `*.conf` — Nginx 설정
- `*.sh` — Shell 스크립트, entrypoint
- `*.json` — package.json, tsconfig 등
- `*.sql` — 마이그레이션 스크립트
- `*.env*` — 환경변수 파일
- `Dockerfile*` — Docker 빌드 파일

## 허용된 작업 (수정 없이 가능)

- `Read` — 파일 읽기
- `Grep` — 코드 검색
- `Glob` — 파일 패턴 검색
- `Bash` (읽기 전용 명령) — `git log`, `git diff`, `ls`, `docker ps` 등

## 절대 금지 (사용자 승인 없이)

- `Edit` — 파일 수정
- `Write` — 파일 생성/덮어쓰기
- `Bash` (파일 변경 명령) — `sed`, `awk`, `echo >`, `cp`, `mv`, `rm`
- `git commit`, `git push` — 코드 커밋/푸시

## 수정이 필요한 경우

**반드시 AskUserQuestion으로 사용자에게 질문한다:**

1. **무엇을**: 어떤 파일의 어떤 부분을 수정하려는지
2. **왜**: 수정이 필요한 이유 (버그, 새 기능, 보안 등)
3. **영향**: 수정이 다른 서비스/모듈에 미치는 영향

사용자가 **명시적으로 "수정해"**, **"변경해"**, **"고쳐"** 등 승인한 경우에만 수정을 진행한다.

## "하는 김에" 수정 절대 금지

- ❌ "코드를 읽다 보니 개선할 점이 있어서 수정"
- ❌ "이 함수 이름이 부적절해 보여서 리팩토링"
- ❌ "타입 오류를 발견해서 수정"
- ❌ "주석 추가/포맷팅 정리"
- ❌ "사용하지 않는 import 제거"

위 모든 경우에도 먼저 사용자에게 보고하고 승인을 받아야 한다.

## 예외

아래 파일만 자유롭게 수정 가능:
- `.claude/rules/*.md` — Claude 규칙 파일
- `.claude/plans/*.md` — 플랜 파일
- `docs/**/*.md` — 문서 파일
- `CLAUDE.local.md` — 로컬 설정
- `C:\Users\서지원\.claude\projects\*\memory\*.md` — 메모리 파일

## 관련 규칙

- `.claude/rules/infra-freeze.md` — 인프라 파일 보호 (더 엄격한 Tier 1/2 분류)
- `.claude/rules/bugfix-root-cause-verification.md` — 버그 수정 원인 확정 게이트
