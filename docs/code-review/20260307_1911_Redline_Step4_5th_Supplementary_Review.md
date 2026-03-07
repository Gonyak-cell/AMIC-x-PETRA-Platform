# Code Review — Redline Step 4 (5th Supplementary Review: 미수행 관점 보완)

> **Review Date**: 2026-03-07 19:11 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: deal-mgmt Step 4 Redline API — 13개 리뷰 관점 중 미수행 3개 관점 보완
> **Method**: 3-Agent Parallel Review (STRIDE + Observability + Deploy Safety)
> **Review Perspectives**: 위협 모델링 & 공격 표면 (STRIDE), 관찰 가능성 & 디버깅 용이성, 배포 안전성
> **Prior Reviews**: 1차~4차 리뷰 (총 128건) + 서브에이전트 2회

## 13개 관점 커버리지 최종 상태

| # | 관점 | 커버 리뷰 | 상태 |
|---|------|----------|------|
| 1 | 보안 (기본) | 2차 | ✅ |
| 2 | **위협 모델링 & 공격 표면 (STRIDE)** | **이번 5차** | ✅ |
| 3 | 데이터 흐름 & 무결성 | 3차 | ✅ |
| 4 | API 계약 & 호환성 | 4차 R4 | ✅ |
| 5 | 에러 처리 | 4차 R5 | ✅ |
| 6 | **관찰 가능성 & 디버깅 용이성** | **이번 5차** | ✅ |
| 7 | 성능 | 4차 R6 + 서브에이전트 | ✅ |
| 8 | **배포 안전성** | **이번 5차** | ✅ |
| 9 | 의존성 & 결합도 | 4차 R9 + 서브에이전트 | ✅ |
| 10 | 도메인 로직 | 4차 R10 + 서브에이전트 | ✅ |
| 11 | 테스트 품질 | 4차 R11 + 서브에이전트 | ✅ |
| 12 | 인지 복잡도 & 가독성 | 4차 R12 + 서브에이전트 | ✅ |
| 13 | 접근성 & UX | N/A (백엔드 전용) | ⬜ |

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1                | P0: 1                |
| High     | 4     | HIGH: 4                | P0: 1 / P1: 3        |
| Warning  | 8     | HIGH: 5 / MEDIUM: 3   | P1: 3 / P2: 5        |
| Suggestion | 5  | MEDIUM: 3 / LOW: 2    | P3: 5                |
| **Total**| **18** | HIGH: **10** / MEDIUM: **6** / LOW: **2** | P0: **2** / P1: **6** / P2: **5** / P3: **5** |

**에이전트별 발견**: STRIDE 9건, 관찰 가능성 8건, 배포 안전성 6건 → 중복 제거 후 **18건**

---

## P0 — 즉시 수정 (배포 차단)

---

### [DEPLOY-C1] `deal-mgmt-api` 컨테이너에 LLM API 키 미주입 — Critical/HIGH

- **관점**: 배포 안전성
- **위치**: `docker-compose.yml:187-225` (deal-mgmt-api environment)
- **신뢰도**: HIGH

**증거**: `deal-mgmt-api` 서비스의 `environment` 블록에 `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`가 없다. 반면 `deal-mgmt-celery-worker`에는 3개 키 모두 주입되어 있다.

**문제**: Step 4는 Celery를 거치지 않고 FastAPI 워커에서 LLM을 직접 호출한다. API 키가 없으므로 `RalphLLMClient.is_available = False` → `RuntimeError: 사용 가능한 LLM 프로바이더가 없습니다.` → HTTP 503.

**영향**: Step 4 기능 전체 불능.

**수정 제안**: `deal-mgmt-api` environment에 추가:
```yaml
ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
OPENAI_API_KEY: ${OPENAI_API_KEY:-}
GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}
```

---

### [STRIDE-R1] Step 4 redline 생성에 감사 로그(Audit Log) 없음 — High/HIGH

- **관점**: STRIDE — Repudiation (부인)
- **위치**: `spa_analysis.py:261-379` (Step 4 전체 핸들러)
- **신뢰도**: HIGH

**증거**: `spa_analysis.py`에서 `audit_service` import 없음. `AuditAction` enum에 Step 4 관련 액션이 미정의. DB에 영구 감사 이력 미기록.

**문제**: M&A 계약서 검토는 법적 증거력이 필요한 고민감 작업. 누가 어떤 거래의 SPA를 redline 처리했는지 추적 불가.

**수정 제안**: Step 4 완료 시 `audit_service`로 DB 기록 — entity_type: `"spa_redline"`, metadata: `{txn_id, user_email, filename, issues_count, model_used, cost_usd}`.

---

## P1 — 우선 수정

---

### [DEPLOY-W1] Dockerfile에 `libxml2`/`libxslt` 런타임 라이브러리 누락 — Warning/HIGH

- **관점**: 배포 안전성
- **위치**: `deal-mgmt/Dockerfile:38-41`
- **신뢰도**: HIGH

**증거**: runtime 스테이지의 `apt-get install` 목록이 `curl`만 포함. `python:3.11-slim-bookworm`은 `libxml2` 런타임을 포함하지 않는다.

**문제**: lxml manylinux wheel이 정적 링크를 포함하는 경우가 많으나, sdist 빌드가 시도되면 빌드 실패. 런타임에 `ImportError: libxml2.so.2` 가능성.

**수정 제안**:
```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*
```

---

### [OBS-W1] LLM 호출 소요 시간 미측정 — Warning/HIGH

- **관점**: 관찰 가능성
- **위치**: `spa_analysis_service.py:2130`
- **신뢰도**: HIGH

**증거**: `result = await _call_llm_json(...)` 호출 전후에 `time.monotonic()` 측정이 없다. Step 4는 30~120초 소요 엔드포인트.

**문제**: 타임아웃 발생 시 병목이 LLM인지 OOXML 처리인지 구분 불가.

---

### [OBS-W2] OOXML 처리 소요 시간 미측정 — Warning/HIGH

- **관점**: 관찰 가능성
- **위치**: `spa_analysis_service.py:2168`
- **신뢰도**: HIGH

**증거**: `await run_in_threadpool(redline_engine.apply_redlines, ...)` 전후 시간 측정 없음.

---

### [OBS-W3] 라우터 에러 로그에 `exc_info=True` 누락 — Warning/HIGH

- **관점**: 관찰 가능성
- **위치**: `spa_analysis.py:329-338`
- **신뢰도**: HIGH

**증거**: `except RuntimeError/ValueError`에서 `logger.error("...error=%s", exc)` — 스택 트레이스 미포함. 같은 파일의 `except Exception:` 블록은 `logger.exception()` 사용(올바름). Step 1~3도 동일 패턴.

---

## P2 — 개선 권장

---

### [STRIDE-S1] 개발 환경 인증 우회 구조 — High/HIGH (기존 코드)

- **관점**: STRIDE — Spoofing
- **위치**: `security.py:58-64`
- **신뢰도**: HIGH

**증거**: `AUTH_ENABLED=False` + `ENV=dev`에서 모든 요청이 ANALYST 권한으로 통과. `ENV`는 런타임 주입 가능.

**비고**: Step 4 신규 코드가 아닌 기존 인증 구조. 프로덕션에서 `AUTH_ENABLED=True`인 한 직접적 위협은 없으나, docker-compose.yml 설정 확인 필요.

---

### [STRIDE-E1] 이메일 대소문자 비교 불일치 — High/HIGH (기존 코드)

- **관점**: STRIDE — Elevation of Privilege
- **위치**: `spa_analysis.py:81-85`
- **신뢰도**: HIGH

**증거**: `txn.lead_advisor_email != claims.email` — 대소문자 구분 비교. `check_client_deal_access`는 `func.lower()` 사용.

**수정 제안**: `.lower()` 비교로 통일.

---

### [STRIDE-D1] 인메모리 Rate Limiter 멀티 워커 무력화 — High/HIGH (기존 코드)

- **관점**: STRIDE — Denial of Service
- **위치**: `spa_analysis.py:38-59`
- **신뢰도**: HIGH

**증거**: `_analysis_rate: dict[str, list[float]] = {}` — 프로세스 로컬. 멀티 워커 환경에서 `3 × N`회 허용.

**비고**: 현재 단일 워커로 배포 중이므로 즉각적 위험은 낮음. 장기적으로 Redis 기반 교체 권장.

---

### [STRIDE-T1] MIME 타입 검증 무력화 — Medium/HIGH

- **관점**: STRIDE — Tampering
- **위치**: `spa_analysis.py:290-299`
- **신뢰도**: HIGH

**증거**: `application/octet-stream` + `application/zip` 허용으로 실질적 모든 바이너리 통과. `content_type is None`이면 검증 스킵.

**수정 제안**: magic bytes 검증 추가 (`b'PK\x03\x04'`), `content_type is None` 거부.

---

### [STRIDE-T2] `_repack_docx` 내 ZIP 엔트리 크기 미검증 — Medium/MEDIUM

- **관점**: STRIDE — Tampering
- **위치**: `redline_engine.py:896-921`
- **신뢰도**: MEDIUM

**증거**: `_read_zip_entry`는 스트리밍 크기 검증을 수행하나, `_repack_docx` 내 `zf_in.read(item.filename)` 직접 호출은 이 보호를 우회.

**수정 제안**: `zf_in.read()` → `_read_zip_entry()` 교체.

---

### [OBS-W4] LLM 타임아웃 발생 시 로깅 부재 — Warning/MEDIUM

- **관점**: 관찰 가능성
- **위치**: `spa_analysis_service.py:184-185`
- **신뢰도**: MEDIUM

**증거**: `except TimeoutError` 캐치 시 `raise RuntimeError(...)` 만 수행, 로그 없음.

---

### [OBS-W5] 이슈 skip 로그에 요약 정보 부족 — Warning/MEDIUM

- **관점**: 관찰 가능성
- **위치**: `redline_engine.py:238-249`
- **신뢰도**: MEDIUM

**증거**: `logger.exception("...issue=%s", issue_id)` — `clause_ref`, `severity` 미포함.

---

## P3 — 저우선

---

### [STRIDE-I1] SPA/실사 문서 전문 외부 LLM 전송 — Medium/HIGH (아키텍처)

- **관점**: STRIDE — Information Disclosure
- **위치**: `spa_analysis_service.py:2127`
- **비고**: 아키텍처 수준 이슈. LLM 제공사 DPA 체결 및 Enterprise API 사용 검토 필요.

---

### [STRIDE-T3] `proposed_redline` 내부 텍스트 길이 미검증 — Medium/MEDIUM

- **관점**: STRIDE — Tampering
- **위치**: `spa_analysis.py:481-496`
- **비고**: `proposed_redline` 전체 최대 10,000자이나 단일 `[INS]` 태그 내용 길이 제한 없음.

---

### [DEPLOY-W2] `docker-compose.yml` 역슬래시 경로 — Warning/MEDIUM

- **위치**: `docker-compose.yml:211`
- **비고**: `.\deal-mgmt:/app` → `./deal-mgmt:/app`. 개발 환경 한정, 프로덕션 비영향.

---

### [OBS-S1] 서비스 함수 진입 시 로그 부재 — Suggestion/MEDIUM

- **위치**: `spa_analysis_service.py:2096-2115`
- **비고**: Step 4 서비스 레이어 진입 시점에 `logger.info()` 없음.

---

### [STRIDE-L1] 파일명 로그 인젝션 가능성 — Low/LOW

- **위치**: `spa_analysis.py:309`
- **비고**: 원본 `filename`에 개행 포함 가능. `safe_name` 사용 권장.

---

## Passed Checks (양호 항목)

### STRIDE 양호 항목
- [x] XXE 방어: `_SAFE_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)`
- [x] LLM 타임아웃: `asyncio.wait_for(..., timeout=120.0)`
- [x] ZIP 내부 파일 스트리밍 크기 제한: `_read_zip_entry` (50MB)
- [x] lxml 자동 XML 이스케이핑으로 XML injection 차단
- [x] 에러 응답에 스택 트레이스 미노출 (HTTPException detail만 반환)
- [x] 파일명 헤더 인젝션 방어 (`re.sub` 필터링)
- [x] 임시 파일 미사용 — 메모리(`io.BytesIO`)만 사용
- [x] Step 4 인증 데코레이터 `Depends(require_write_access())` 적용

### 관찰 가능성 양호 항목
- [x] `logging.getLogger(__name__)` — 3개 파일 모두 올바르게 사용
- [x] 민감 데이터 로깅 없음 (JWT/PII 미포함)
- [x] LLM 프롬프트 전체 미로깅 + `del user_prompt, spa_text` 메모리 조기 해제
- [x] 이슈 성공/실패 건수 집계: `issues_count`, `skipped_count` 반환 + 헤더 노출
- [x] 매칭 실패 디버깅: `original_target_text[:50]` warning 포함
- [x] 에러 메시지 구체적 (모호한 메시지 없음)
- [x] 예외 체이닝 (`from exc`) 일관 적용

### 배포 안전성 양호 항목
- [x] `lxml>=5.0.0`이 `pyproject.toml` dependencies에 등록
- [x] `hatchling` 빌드 백엔드 + `packages = ["app"]` — Guard 6 통과
- [x] `[project.optional-dependencies] dev` 사용 — Guard 7 통과
- [x] `ruff per-file-ignores`에 `redline_engine.py = ["N806"]` 등록
- [x] CPU-bound 작업 `run_in_threadpool` 위임 확인
- [x] XXE + ZIP Slip + ZIP Bomb 방어 확인
- [x] 파일 업로드 확장자 + MIME 이중 검증 + 크기 제한 (20MB)
- [x] DB 스키마 변경 없음 — 무중단 배포 가능
- [x] `deploy.yml` permissions 보존 (Guard 1) + `deal-mgmt/` 변경 감지 정상

---

## Methodology

- **Agents**: backend-security-reviewer (STRIDE), python-code-reviewer ×2 (Observability, Deploy Safety)
- **Files scanned**: 9 (spa_analysis.py, spa_analysis_service.py, redline_engine.py, redline_prompts.py, spa_analysis.py schemas, pyproject.toml, Dockerfile, docker-compose.yml, deploy.yml)
- **Protocol**: Verified Claim Protocol v1.1
- **중복 제거**: Rate Limiter 이슈 (STRIDE + Deploy 양쪽 발견) → 1건으로 병합
