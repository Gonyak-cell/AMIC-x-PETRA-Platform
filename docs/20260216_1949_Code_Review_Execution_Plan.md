# AMIC x PETRA 플랫폼 전체 코드 리뷰 세부 실행 계획

**작성일**: 2026-02-16 19:49
**버전**: VCP v1.1 (Verified Claim Protocol + 신뢰도 가중 우선순위)
**목적**: 재설계된 코드 리뷰 아키텍처 기반 전체 프로젝트 세부항목별 리뷰 계획 수립

---

## Context (컨텍스트)

### 배경

AMIC x PETRA 플랫폼은 2026-02-16에 코드 리뷰 아키텍처를 재설계하여 **허위 양성(False Positive) 문제**를 해결했습니다. 주요 개선사항:

1. **Phase 0B 검증 게이트**: 백엔드 가용성 체크, 범위-에이전트 필터링으로 환각 방지
2. **신뢰도 가중 우선순위**: MEDIUM 신뢰도 → P0 대신 P1으로 하향 조정
3. **Phase 2B 자동 검증**: Moderate/Minor 이슈 100% 검증 (기존 30% → 100%)
4. **VCP v1.1**: 5단계 검증 + 추론 근거 감사 추적

### 현재 상황

- **프론트엔드**: 3개 모듈(FDD, KIIS, IM) 완전 구현
- **백엔드**: 3개 시스템(FDD, KIIS, IM) 존재하나 현재 프로젝트에 포함 여부 미확인
- **인프라**: Docker, Nginx, CI/CD 설정 완료
- **코드 리뷰 시스템**: 12개 전문 에이전트 + 3개 스킬 + VCP 프로토콜 준비 완료

### 문제점

현재까지 **체계적인 전체 코드 리뷰를 실행한 적이 없습니다**. 각 모듈과 영역별로 어떤 항목을 어떤 순서로 리뷰해야 하는지 명확한 계획이 필요합니다.

### 목표

재설계된 코드 리뷰 아키텍처를 활용하여 **전체 프로젝트의 세부항목별 리뷰 계획**을 수립하고, 우선순위에 따라 단계적으로 실행할 수 있는 로드맵을 제시합니다.

---

## 추천 접근법

### 1. 리뷰 범위 정의

#### 1.1 프론트엔드 모듈별 우선순위

| 모듈 | 경로 | 페이지 | 훅 | 우선순위 | 이유 |
|------|------|--------|-----|----------|------|
| **KIIS** | `src/modules/kiis/` | 17개 | 12개 | **P0** | 최고 복잡도 — 가장 많은 페이지/훅 |
| **FDD** | `src/modules/fdd/` | 11개 | 9개 | **P1** | 레퍼런스 패턴 검증 — 다른 모듈 기준 |
| **IM** | `src/modules/im/` | 4개 | 2개 | **P2** | 비교적 단순 |

#### 1.2 공통 영역별 우선순위

| 영역 | 파일 | 우선순위 | 이유 |
|------|------|----------|------|
| **인증/보안** | AuthProvider, ProtectedRoute, useAuth, token-storage | **P0** | 전체 시스템 보안 기반 |
| **API 클라이언트** | client.ts, {fdd/kiis/im}Client.ts | **P0** | 모든 모듈의 백엔드 통신 기반 |
| **레이아웃** | AppShell, Sidebar, ModuleSwitcher, PageHeader | **P1** | 사용자 경험 핵심 |
| **UI 컴포넌트** | 16개 컴포넌트 (Badge, Button, Card, DataTable 등) | **P2** | 재사용 컴포넌트 |
| **공통 훅** | useAnalytics, useNotifications, useGlobalSearch | **P1** | 플랫폼 기능 |
| **유틸리티** | cn, format, storage, ics, sentry | **P2** | 헬퍼 함수 |

#### 1.3 백엔드 및 인프라

| 영역 | 파일 | 우선순위 | 조건 |
|------|------|----------|------|
| **백엔드** | `Auto FDD/backend/`, `KIIS/`, `IM Module/` | **P1** | Phase 0B에서 available로 확인된 경우만 |
| **Docker** | Dockerfile, docker-compose.prod.yml | **P0** | 배포 필수 |
| **Nginx** | nginx/prod.conf, nginx/prod-nossl.conf | **P0** | 보안 헤더, 프록시 설정 |
| **빌드 설정** | vite.config.ts, tsconfig.json | **P1** | 번들링 최적화 |

---

### 2. 에이전트별 세부 검증 항목

각 에이전트가 검증할 핵심 항목을 모듈/영역별로 정의합니다.

#### 2.1 code-reviewer (프론트엔드 코드 품질)

**FDD 모듈**:
- [ ] Deal CRUD 패턴 일관성 (useDeals 훅 vs 페이지)
- [ ] 워크플로우 상태 관리 (Upload → Mapping → Definition → Report)
- [ ] VDR 폴더 트리 재귀 렌더링 최적화
- [ ] Report 버전 관리 UI 일관성

**KIIS 모듈**:
- [ ] SearchBar 컴포넌트 재사용 일관성
- [ ] Company/Fund/Manager/REIT 상세 페이지 패턴
- [ ] Watchlist 낙관적 업데이트
- [ ] Dashboard KPI 차트 데이터 흐름
- [ ] Entity Resolution UI 피드백

**IM 모듈**:
- [ ] 문서 생성 워크플로우 단계별 검증
- [ ] ProgressTracker 진행 상태 동기화
- [ ] DocumentStatusBadge 상태 매핑

**공통 영역**:
- [ ] AuthProvider 토큰 갱신 로직 경쟁 조건
- [ ] ProtectedRoute 리디렉션 루프 방지
- [ ] CommandPalette 키보드 충돌 방지
- [ ] DataTable 정렬/필터링 상태 관리
- [ ] Modal 중첩 시 z-index 관리

#### 2.2 security-auditor (보안 취약점)

- [ ] JWT 토큰 localStorage 저장 (XSS 방지 대안 검토)
- [ ] 리프레시 토큰 경쟁 조건 방지
- [ ] `dangerouslySetInnerHTML` 사용 여부
- [ ] 파일 업로드 확장자/MIME 검증
- [ ] LLM 프롬프트 인젝션 (IM 모듈)
- [ ] 하드코딩된 API 키, 비밀번호
- [ ] CORS/CSP 설정

#### 2.3 api-auditor (FE-BE API 통합)

- [ ] 모든 모듈이 createApiClient 사용
- [ ] 401 → 토큰 갱신 → 재시도 로직
- [ ] Vite 프록시 매핑 정확성
- [ ] API 엔드포인트 일치성 (백엔드 available 시)
- [ ] 에러 응답 처리 (400/401/403/404/500)

#### 2.4 test-auditor (테스트 품질)

- [ ] 각 모듈 훅 테스트 존재 여부
- [ ] Mock 데이터가 백엔드 스키마 일치
- [ ] MSW 핸들러가 Vite 프록시 경로 매칭
- [ ] 테스트 커버리지 누락 영역
- [ ] E2E 주요 워크플로우 커버

#### 2.5 perf-auditor (성능)

- [ ] 코드 스플리팅 (React.lazy)
- [ ] 불필요한 리렌더링
- [ ] VDR 폴더 트리 가상화
- [ ] 이미지 lazy loading
- [ ] API 요청 캐싱 설정

#### 2.6 infra-auditor (인프라)

- [ ] 멀티 스테이지 빌드
- [ ] SPA 라우팅 지원 (try_files)
- [ ] Gzip 압축
- [ ] SSL/TLS 설정
- [ ] 보안 헤더 (CSP, HSTS)

---

### 3. 리뷰 실행 파이프라인

**Phase 0A: Quality Gates** (5-10분)
```bash
cd amic-platform
npx tsc --noEmit
npm run lint
npm run test
npm run build
```

**Phase 0B: Review Gates** (30초-1분)
- 백엔드 가용성 체크
- 범위-에이전트 필터링

**Phase 1: Verified Review** (30-40분, 병렬)
- 에이전트 매트릭스에 따라 병렬 실행
- 모든 이슈에 VCP 프로토콜 적용

**Phase 2: Cross-Verification** (10-20분)
- Critical + Major 이슈 교차 검증

**Phase 2B: Auto-Verification** (5-10분)
- Moderate + Minor 이슈 자동 검증

**Phase 3: Report Assembly** (2-5분)
- 신뢰도 가중 우선순위 계산
- 리포트 생성

---

### 4. 실행 가능한 커맨드 시퀀스

#### 4.1 전체 프로젝트 리뷰
```bash
/review-full
```
**예상 소요 시간**: 60-90분
**대상**: 전체 코드베이스

#### 4.2 모듈별 집중 리뷰

**KIIS 모듈 (최우선)**:
```bash
/review-full --module kiis
```
**예상 소요 시간**: 45-60분

**FDD 모듈 (레퍼런스 검증)**:
```bash
/review-full --module fdd
```
**예상 소요 시간**: 30-40분

**IM 모듈**:
```bash
/review-full --module im
```
**예상 소요 시간**: 20-30분

#### 4.3 전문 리뷰

**보안 집중**:
```bash
/review-security
```
**예상 소요 시간**: 30-45분

**테스트 품질**:
```bash
/review-test
```
**예상 소요 시간**: 15-25분

**성능**:
```bash
/review-perf
```
**예상 소요 시간**: 20-30분

**인프라**:
```bash
/review-infra
```
**예상 소요 시간**: 15-20분

#### 4.4 PR 검토용 (변경 파일만)
```bash
/review-full --diff
/review-full --diff main
```
**예상 소요 시간**: 10-20분

---

### 5. 권장 실행 일정

#### 1주차: 핵심 영역 (P0)
- **Day 1**: `/review-security` (인증, API 클라이언트, 보안)
- **Day 2**: `/review-full --module kiis` (최고 복잡도)
- **Day 3**: `/review-full --module fdd` (레퍼런스 검증)

#### 2주차: 중요 영역 (P1)
- **Day 4**: `/review-full --module im` + 공통 API 리뷰
- **Day 5**: 공통 레이아웃 + UI 컴포넌트 리뷰
  ```bash
  /review-full --files src/components/layout/*.tsx src/components/ui/*.tsx
  ```

#### 3주차: 품질/성능 (P2)
- **Day 6**: `/review-test` + `/review-perf`
- **Day 7**: `/review-infra`

#### 지속적 리뷰
- **PR 생성 시**: `/review-full --diff main`
- **머지 전**: `/review-full --diff main --severity critical`

---

### 6. 리포트 확인 및 후속 조치

각 리뷰 완료 후:

1. **리포트 확인**:
   - 경로: `docs/YYYYMMDD_HHMM_{Scope}_Code_Review.md`
   - 우선순위 매트릭스 확인 (P0 → P1 → P2 → P3)

2. **허위 양성 검증** (선택적):
   ```bash
   /verify-review
   ```
   - 의심스러운 이슈 재검증
   - 거부 사유 분류 확인

3. **수정 작업**:
   - P0 이슈: 즉시 수정 (보안/데이터)
   - P1 이슈: 스프린트 우선
   - P2/P3 이슈: 백로그

---

## 핵심 파일

### 코드 리뷰 시스템

1. **오케스트레이터**:
   - `amic-platform/.claude/skills/review-orchestrate/SKILL.md`
   - 4단계 파이프라인 (Phase 0A/0B/1/2/2B/3)

2. **VCP 프로토콜**:
   - `amic-platform/.claude/rules/verified-claim-protocol.md`
   - 5단계 검증 + 신뢰도 가중 우선순위 공식

3. **검증 게이트**:
   - `amic-platform/.claude/rules/review-gates.md`
   - Phase 0B 백엔드 체크, 범위 필터링

4. **자동 검증 스킬**:
   - `amic-platform/.claude/skills/auto-verify/SKILL.md`
   - Moderate/Minor 이슈 자동 검증

5. **주요 에이전트**:
   - `amic-platform/.claude/agents/code-reviewer.md`
   - `amic-platform/.claude/agents/security-auditor.md`
   - `amic-platform/.claude/agents/api-auditor.md`
   - `amic-platform/.claude/agents/review-verifier.md`

### 프로젝트 구조

**프론트엔드**:
- FDD: `amic-platform/src/modules/fdd/`
- KIIS: `amic-platform/src/modules/kiis/`
- IM: `amic-platform/src/modules/im/`
- 공통: `amic-platform/src/components/`, `amic-platform/src/hooks/`

**백엔드** (Phase 0B 체크 대상):
- FDD: `Auto FDD/backend/`
- KIIS: `KIIS/`
- IM: `IM Module/auto-im-generator/`

**인프라**:
- Docker: `Dockerfile`, `docker-compose.prod.yml`
- Nginx: `nginx/prod.conf`, `nginx/prod-nossl.conf`
- 빌드: `amic-platform/vite.config.ts`

---

## 검증 방법

### 1. 파이프라인 정상 작동 확인

테스트 리뷰 실행:
```bash
/review --files amic-platform/src/App.tsx
```

**확인 사항**:
- Phase 0A Quality Gates 실행 (tsc, lint, test, build)
- Phase 0B Review Gates 실행 (백엔드 체크)
- Phase 1 에이전트 호출
- VCP 프로토콜 준수 (검증 추적 섹션 존재)
- 신뢰도 가중 우선순위 계산
- 리포트 생성 (`docs/` 디렉터리)

### 2. 우선순위 계산 검증

리포트에서 확인:
```markdown
- **우선순위**: P1 (점수: 60)
  - 심각도 가중치: 100
  - 신뢰도 가중치: 0.6
  - 보너스: +0
  - ⚠️ 이 치명적 이슈는 중간 신뢰도로 인해 P1으로 분류되었습니다.
```

**공식 검증**:
- Critical (100) × MEDIUM (0.6) = 60 → P1 ✓

### 3. 허위 양성 방지 확인

리포트 말미 확인:
```markdown
## 검증 투명성
- 검증한 가설: N건
- 거부된 가설: N건
- 보고된 이슈: N건
- 거부율: X%
```

**목표**: 거부율 10-30% (건전한 검증 활동)

### 4. Phase 2B 자동 검증 확인

Moderate/Minor 이슈가 있을 때:
```markdown
Phase 2B 자동 검증:
- Moderate 이슈: 18/23건 검증됨 (78%)
- Minor 이슈: 12/15건 검증됨 (80%)
- 수동 검토 플래그: 8건
```

**목표**: 검증 범위 100% (모든 Moderate/Minor 처리)

---

## 성공 지표

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| **허위 양성 비율** | <10% | verify-review 실행 후 FP 비율 |
| **검증 범위** | 100% | Phase 2 + Phase 2B 모두 실행 |
| **우선순위 정확도** | P0 이슈의 90%+ HIGH 신뢰도 | 리포트 Summary 테이블 확인 |
| **리뷰 속도** | 전체 60-90분, 변경파일 10-20분 | 실행 시간 측정 |
| **거부율** | 10-30% | 리포트 검증 투명성 섹션 |

---

## 다음 단계

1. **즉시 실행**: `/review-security` (인증/보안 핵심 영역)
2. **KIIS 모듈 리뷰**: `/review-full --module kiis` (최고 복잡도)
3. **FDD 레퍼런스 검증**: `/review-full --module fdd`
4. **리포트 분석**: 우선순위 매트릭스 기반 수정 계획 수립
5. **지속적 통합**: PR 기반 리뷰 워크플로우 정착
