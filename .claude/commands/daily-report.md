---
name: daily-report
description: "일일 작업 리포트를 생성합니다. 사용법: /daily-report [YYYY-MM-DD] (기본: 어제)"
---

# 일일 작업 리포트 생성

대상 날짜: $ARGUMENTS (인자 미제공 시 기본값: 어제)

## 실행 순서

1. 리포트 생성 스크립트를 실행합니다:
   ```bash
   python .claude/skills/daily-report/scripts/generate_daily_report.py --date "${ARGUMENTS:-$(date -d 'yesterday' +%Y-%m-%d)}" --project-dir "$CLAUDE_PROJECT_DIR"
   ```

2. 생성된 `logs/daily/YYYY-MM-DD.md` 파일을 Read합니다.

3. 다음 형식으로 핵심 내용을 요약합니다:
   - **일일 요약**: 커밋 수, 에러 수, 수정률
   - **주요 에러**: 에러 추적표에서 상위 5건 (카테고리, 에러 내용, 수정 여부, 재발 가능성)
   - **인사이트**: 패턴 분석 결과, 개선 제안

4. 리포트에 미해결(UNRESOLVED) 또는 재발 위험 HIGH인 에러가 있으면:
   - 우선적으로 해결해야 할 항목을 별도로 강조합니다
   - 해결 방안을 제안합니다

5. 리포트가 이미 존재하면 기존 리포트를 Read하여 요약만 표시합니다.

## 참고

- 리포트 저장 위치: `logs/daily/YYYY-MM-DD.md`
- 데이터 소스: `logs/errors.jsonl`, `logs/prompts.jsonl`, `git log`
- 에러-수정 연결: 파일 경로 매칭 + 시간 근접 매칭 + 세션 맥락 추출
