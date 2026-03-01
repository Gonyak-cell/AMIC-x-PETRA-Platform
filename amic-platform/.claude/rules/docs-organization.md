# 문서 저장 및 분류 규칙

> 생성: 2026-02-17 18:12

## 기본 원칙

1. **모든 문서는 `docs/` 하위의 카테고리 폴더에 저장한다** — 루트 `docs/`에 직접 저장 금지
2. **파일명 형식**: `YYYYMMDD_HHMM_{주제}.md` (시스템 파일 예외)
3. **새 문서 추가 시 `docs/INDEX.md`를 반드시 업데이트한다**

## 카테고리 폴더 및 분류 기준

| 폴더 | 대상 | 분류 키워드 |
|------|------|------------|
| `docs/architecture/` | 전체 프로젝트 구조, 통합 계획, 포털 설계, 설정 표준화 | 통합, 구조, 포털, 설정, 전체, architecture |
| `docs/code-review/` | 코드 리뷰 리포트, 프롬프트, 리뷰 프로토콜 | Code Review, 리뷰, 리포트, 프롬프트, VCP |
| `docs/security/` | 보안 감사, 인증/인가, JWT, CORS | Security, JWT, 인증, XSS, CORS, 보안 |
| `docs/deployment/` | 배포 체크리스트, 빌드 리포트, CI/CD, Docker | Deploy, 배포, 빌드, CI/CD, Docker, 인프라 |
| `docs/fdd/` | FDD 모듈 전용 (워크플로, 템플릿, LLM 프롬프트) | FDD, 실사, Due Diligence |
| `docs/kiis/` | KIIS 모듈 전용 (구현 계획, 펀드, REIT, 공시) | KIIS, 펀드, REIT, 공시, 핵심투자설명서 |
| `docs/im/` | IM 모듈 전용 (워크플로, 템플릿, 시각화) | IM, 투자설명서, Information Memorandum |
| `docs/frontend/` | 프론트엔드 공통 (UI/UX, 컴포넌트, MSW, 테스트 목) | UI, UX, 컴포넌트, MSW, 프론트엔드, Tailwind |
| `docs/testing/` | 테스트 계획, E2E, 단위 테스트 전략 | E2E, 테스트, Playwright, Vitest, 테스트 전략 |

## 분류 우선순위 (복수 카테고리 해당 시)

문서가 여러 카테고리에 걸칠 경우 아래 우선순위로 판단:

1. **모듈 전용** (`fdd/`, `kiis/`, `im/`) — 특정 모듈이 주 대상이면 해당 모듈 폴더
2. **보안** (`security/`) — 보안이 핵심 주제이면 보안 폴더
3. **배포** (`deployment/`) — 배포/인프라가 핵심이면 배포 폴더
4. **코드 리뷰** (`code-review/`) — 리뷰 리포트/프로토콜이면 코드 리뷰 폴더
5. **프론트엔드** (`frontend/`) — 프론트엔드 공통이면 프론트엔드 폴더
6. **테스트** (`testing/`) — 테스트 전략/계획이면 테스트 폴더
7. **아키텍처** (`architecture/`) — 전체 구조/통합이면 아키텍처 폴더

## 문서 작성 워크플로

```
1. 카테고리 결정 → 위 테이블 참조
2. 타임스탬프 확인 → PowerShell: Get-Date -Format "yyyyMMdd_HHmm"
3. 파일 생성 → docs/{카테고리}/YYYYMMDD_HHMM_{주제}.md
4. INDEX.md 업데이트 → 해당 카테고리 섹션에 행 추가
```

## 문서 수정 워크플로

```
1. 타임스탬프 확인 → PowerShell: Get-Date -Format "yyyyMMdd_HHmm"
2. 문서 내용 수정
3. 파일명의 타임스탬프를 수정 시점으로 갱신
   예: 20260219_0046_Plan.md → 20260220_1412_Plan.md
4. INDEX.md 업데이트 → 파일명 변경 반영
```

> **핵심**: 파일명 타임스탬프는 작성 시점이 아닌 **마지막 수정 시점** 기준
> 상세 규칙: `doc-filename-timestamp.md` 참조

## 새 카테고리 추가 시

- `docs/INDEX.md`의 폴더 구조 테이블에 행 추가
- 이 규칙 파일(`docs-organization.md`)의 카테고리 테이블에 행 추가
- 필요 시 MEMORY.md 업데이트

## 예외

- `docs/INDEX.md` — 색인 파일, 루트에 유지
- `review/` — 코드 리뷰 수정 내역 (별도 관리, `/review-orchestrate` 스킬 `docs/documentation.md` 참조)
- `CLAUDE.md`, `CLAUDE.local.md`, `README.md`, `MEMORY.md` — 시스템 파일
