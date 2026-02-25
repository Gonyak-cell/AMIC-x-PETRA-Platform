---
name: bug-report
description: "최근 에러 로그를 분석하여 반복 버그 패턴 리포트를 생성합니다. 사용법: /bug-report [days=30]"
---

# 버그 패턴 리포트

분석 기간: 최근 $ARGUMENTS 일 (인자 미제공 시 기본값: 30일)

## 실행 순서

1. `logs/errors.jsonl` 파일 존재 여부를 확인합니다.
   - 파일이 없으면 "에러 로그가 아직 없습니다. 작업을 진행하면 자동으로 에러가 기록됩니다." 안내 후 종료.

2. 분석 스크립트를 실행합니다:
   ```bash
   python .claude/skills/bug-feedback/scripts/analyze_bugs.py --days ${ARGUMENTS:-30}
   ```

3. 생성된 `knowledge/bug-patterns.md` 파일을 Read합니다.

4. 다음 형식으로 리포트를 출력합니다:
   - **기간 내 총 에러 건수**
   - **카테고리별 분포** (표 형식)
   - **TOP 5 반복 패턴** (에러 내용 + 해결 방법)
   - **최근 7일 에러 트렌드** (증가/감소)
   - **권장 조치사항** (가장 빈번한 에러에 대한 예방책)

5. 반복 패턴 중 P1 이상(5회 이상 반복)이 있으면:
   - `review/bugfix/` 폴더에 문서화할지 사용자에게 확인합니다.
   - 해당 패턴에 대해 **방지 규칙**을 `.claude/rules/`에 추가할지 제안합니다.

## 출력 형식 예시

```
## 에러 패턴 리포트 (최근 30일)

### 요약
- 총 에러: 45건 | 고유 패턴: 12개 | 반복 패턴: 3개

### 반복 패턴 TOP 5

| # | 카테고리 | 에러 | 횟수 | 해결 방법 |
|---|---------|------|------|----------|
| 1 | build | Cannot find module... | 7 | tsconfig paths 확인 |
| 2 | test | fixture not found | 5 | conftest.py 경로 확인 |

### 권장 조치
1. TypeScript 모듈 에러가 빈번합니다 → import 경로 자동 검증 추가 권장
```
