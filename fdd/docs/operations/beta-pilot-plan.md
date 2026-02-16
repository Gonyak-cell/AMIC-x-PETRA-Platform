# Auto FDD — Beta Pilot 실행 계획

> Sprint 13 Track A5 | 상태: Ready for Launch

---

## 1. 파일럿 개요

| 항목 | 내용 |
|------|------|
| 목표 | 실 사용자 환경에서 FDD 워크플로우 검증 |
| 기간 | 2주 (Day 1 ~ Day 14) |
| 파트너 수 | 2~3개사 |
| 대상 딜 | 파트너당 1~2건의 실제/유사 FDD 케이스 |
| 성공 기준 | 전체 워크플로우 완료율 80%+, 치명적 버그 0건 |

---

## 2. 사전 준비 체크리스트

### 2.1 인프라

- [ ] `.env.production` 설정 완료 (`.env.production.example` 참조)
- [ ] SSL 인증서 발급 (`scripts/setup-ssl.sh`)
- [ ] Staging 서버 배포 (`scripts/deploy.sh up`)
- [ ] 모니터링 스택 구동 (`docker-compose.monitoring.yml`)
- [ ] Grafana 대시보드 접속 확인 (`:3000`)
- [ ] 알림 규칙 적용 (`config/prometheus/alert-rules.yml`)
- [ ] DB 백업 스케줄 설정 (`scripts/deploy.sh backup`)

### 2.2 데이터

- [ ] 샘플 TB 파일 준비 (`sample-tb.xlsx` — 20개 계정)
- [ ] 샘플 GL 파일 준비 (`sample-gl.xlsx` — 50건 전표)
- [ ] 테스트 딜 생성 및 전체 워크플로우 사전 검증

### 2.3 계정

- [ ] Admin 계정 생성 (`scripts/deploy.sh create-admin`)
- [ ] 파트너별 ANALYST 계정 생성
- [ ] 임시 비밀번호 발급 (최초 로그인 시 변경)

---

## 3. 파일럿 스케줄

```
Week 1: 온보딩 + 실습
  Day 1-2   파트너 킥오프 미팅 + 시스템 교육 (2시간)
  Day 3-4   샘플 딜 실습 (자체 진행, 온라인 지원)
  Day 5     첫 실제 딜 적용 시작

Week 2: 실전 + 피드백
  Day 6-8   실제 딜 진행 (일일 스탠드업 15분)
  Day 9-10  보고서 생성 및 검토
  Day 11    피드백 수집 (양식 + 인터뷰)
  Day 12-14 결과 정리 및 개선사항 반영
```

---

## 4. 모니터링 SLA

파일럿 기간 중 아래 SLA를 모니터링합니다.

| 지표 | 목표 | 알림 기준 |
|------|------|-----------|
| 서비스 가용성 | 99%+ | Backend Down > 1분 |
| 에러율 (5xx) | < 1% | 5분간 1% 초과 시 Warning |
| API 응답 (p95) | < 5초 | p95 > 5초 시 Warning |
| GL 인제스트 (100K) | < 30초 | SLA 초과 시 Error |
| PPT 렌더링 | < 120초 | SLA 초과 시 Error |

### 4.1 모니터링 접속 정보

| 서비스 | URL | 인증 |
|--------|-----|------|
| Grafana | `https://<domain>:3000` | admin / (env에 설정) |
| Prometheus | `https://<domain>:9090` | IP 제한 |
| 앱 Health | `https://<domain>/health` | 공개 |

---

## 5. 지원 체계

| 레벨 | 채널 | 응답 시간 | 담당 |
|------|------|-----------|------|
| L1 일반 문의 | Slack / Email | 24시간 이내 | PM |
| L2 기능 오류 | Slack (긴급) | 4시간 이내 | Dev Lead |
| L3 시스템 장애 | 전화 / Slack | 1시간 이내 | SRE |

### 5.1 에스컬레이션 절차

1. 파트너가 L1 채널로 이슈 리포트
2. PM이 재현 확인 → GitHub Issue 생성
3. Severity 분류:
   - **P0 (Critical)**: 전체 서비스 불가 → 즉시 Hotfix
   - **P1 (Major)**: 핵심 기능 장애 → 24시간 내 Fix
   - **P2 (Minor)**: 불편사항 → 다음 스프린트 반영
   - **P3 (Cosmetic)**: UI/UX 개선 → Backlog

---

## 6. 피드백 수집

### 6.1 수집 방법

| 방법 | 시점 | 대상 |
|------|------|------|
| 일일 스탠드업 메모 | 매일 (Week 2) | 실무자 |
| 피드백 양식 | Day 11 | 전체 참여자 |
| 1:1 인터뷰 (30분) | Day 11-12 | 핵심 사용자 |
| 시스템 로그 분석 | Day 14 | 자동 수집 |

### 6.2 피드백 양식

`docs/operations/partner-onboarding.md` 섹션 6 참조.

### 6.3 정량적 지표 수집

| 지표 | 측정 방법 |
|------|-----------|
| 워크플로우 완료율 | 딜 생성 → 보고서 생성 완료 비율 |
| 평균 딜 소요 시간 | 딜 생성 ~ 보고서 완료 시간 |
| 에러 발생 빈도 | Prometheus 에러 카운터 |
| 사용자 만족도 | 피드백 양식 점수 (1~5) |

---

## 7. 롤백 절차

문제 발생 시 롤백 순서:

1. 현재 상태 백업: `./scripts/deploy.sh backup`
2. 서비스 중단: `./scripts/deploy.sh down`
3. 이전 버전 체크아웃: `git checkout <previous-tag>`
4. 재배포: `./scripts/deploy.sh up`
5. 헬스체크 확인: `./scripts/deploy.sh health`
6. 파트너 공지: Slack/Email로 상황 안내

상세: `docs/operations/rollback-procedure.md` 참조.

---

## 8. 파일럿 완료 기준

| 기준 | 목표 | 측정 |
|------|------|------|
| 워크플로우 완료 | 각 파트너 최소 1건 FDD 완료 | 시스템 기록 |
| 보고서 생성 | PPT/Word 보고서 정상 출력 | 파일 검증 |
| 치명적 버그 | 0건 | Issue Tracker |
| 사용자 만족도 | 평균 3.5/5.0 이상 | 피드백 양식 |
| 데이터 정합성 | TB/GL 숫자 불일치 0건 | QA 엔진 결과 |

---

## 9. 파일럿 후 조치

1. **피드백 종합 리포트** 작성 (PM)
2. **버그/개선사항** GitHub Issues로 정리
3. **우선순위 결정** (P0~P3 분류)
4. **Sprint 14 계획**에 피드백 반영
5. **GA (General Availability) 판단** — 파일럿 성공 기준 충족 여부
