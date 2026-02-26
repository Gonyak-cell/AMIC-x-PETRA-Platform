# daily-report

일일 작업 리포트를 자동 생성하는 스킬.

## 목적

매일 00:00~24:00 동안의 코드 변경, 에러 발생/수정, 작업 맥락을 자동 문서화한다.

## 구성

| 파일 | 역할 |
|------|------|
| `scripts/generate_daily_report.py` | 핵심 리포트 생성 엔진 |
| `scripts/error_fix_linker.py` | 에러-수정 연결 알고리즘 (3단계 히어리스틱) |

## 데이터 흐름

```
logs/errors.jsonl    ─┐
logs/prompts.jsonl   ─┤─→ generate_daily_report.py ─→ logs/daily/YYYY-MM-DD.md
git log              ─┘       │
                              └─→ error_fix_linker.py (에러↔커밋 연결)
```

## 리포트 구조 (6개 섹션)

1. **일일 요약**: 커밋, 파일, 에러, 세션 통계
2. **커밋별 수정 내역**: conventional commit 파싱, 변경 파일
3. **에러 추적표**: 에러 유형, 내용, 수정 취지, 수정 여부, 발생/수정 맥락, 재발 가능성
4. **세션 타임라인**: 시간대별 작업 흐름
5. **카테고리별 에러 분포**: 유형별 건수, 비율, 수정률
6. **주요 인사이트**: 자동 패턴 분석

## 자동 실행

- `UserPromptSubmit` 훅에서 전날 리포트 미존재 시 자동 생성
- `/daily-report [날짜]` 커맨드로 수동 실행 가능

## 에러-수정 연결 알고리즘

| 단계 | 방법 | 신뢰도 |
|------|------|-------|
| 1 | 파일 경로 매칭 (에러 파일 ↔ 커밋 변경 파일) | HIGH |
| 2 | 시간 근접 매칭 (30분 내 fix 커밋) | MEDIUM |
| 3 | 세션 맥락 추출 (동일 세션 프롬프트) | 보조 |

## 수정 상태

- FIXED: fix 커밋 연결 + 이후 미재발
- LIKELY_FIXED: 커밋 존재 + 세션 내 미재발
- WORKAROUND: 수정했지만 재발
- UNRESOLVED: 수정 커밋 없음
- RECURRING: 3회+ 반복

## 재발 가능성

- LOW: 코드 수정 + 테스트 추가
- MEDIUM: 코드 수정만
- HIGH: 환경 의존적 / 3일+ 반복 / 미해결
