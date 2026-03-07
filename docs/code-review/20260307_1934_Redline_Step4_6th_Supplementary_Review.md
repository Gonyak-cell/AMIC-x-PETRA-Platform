# Code Review — Redline Step 4 (6th Supplementary Review)

> **Review Date**: 2026-03-07 19:34
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: deal-mgmt Redline Engine Step 4 — R3(Data Flow), R4(API Contract), R6(Observability), R7(Performance)
> **Method**: Review Gates + Verified Multi-Agent Review (4 parallel agents)
> **Quality Gates**: ruff(PASS) pytest(PASS, 66/66)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1                | P0: 1                |
| Major/High | 3  | HIGH: 3                | P1: 3                |
| Moderate/Medium | 3 | HIGH: 2 / MEDIUM: 1 | P2: 3             |
| Minor/Low | 6   | HIGH: 2 / MEDIUM: 4   | P3: 6                |
| Suggestion | 3  | —                      | —                    |
| **Total** | **16** | HIGH: **8** / MEDIUM: **5** / LOW: **0** | P0: **1** / P1: **3** / P2: **3** / P3: **6** |

**FP Prevention**: R3 에이전트가 lxml thread-safety 가설 검증 후 안전 확인 (FP 1건 사전 거부)

---

## Findings

### P0 — 즉시 수정 (점수: 90+)

#### [R4-C1] CORS expose_headers 누락 — Content-Disposition 헤더 브라우저 접근 불가 — [Critical/HIGH] — Priority: P0

**파일**: [main.py:129-136](deal-mgmt/app/main.py#L129-L136)

**문제**: `CORSMiddleware` 설정에 `expose_headers`가 없어 브라우저 JavaScript가 `Content-Disposition` 헤더를 읽을 수 없음. Step 4 응답은 `StreamingResponse`로 `.docx` 파일을 반환하며, 프론트엔드에서 파일명을 추출하려면 이 헤더 접근이 필수.

**증거**:
```python
# deal-mgmt/app/main.py:129-136
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # expose_headers 미설정 → 브라우저가 Content-Disposition 접근 불가
)
```

**수정안**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
```

**심각도 근거**: CORS 스펙상 `expose_headers` 없으면 브라우저는 simple response headers만 접근 가능. Content-Disposition은 simple header가 아니므로 프론트엔드 파일 다운로드 로직이 완전히 차단됨.

---

### P1 — 스프린트 우선 (점수: 60-89)

#### [R4-M1] industry_type 정규식 불일치 — Form 파라미터와 프롬프트 플레이스홀더 매핑 오류 — [Major/HIGH] — Priority: P1

**파일**: [spa_analysis.py:194](deal-mgmt/app/routers/spa_analysis.py#L194)

**문제**: `industry_type` Form 파라미터에 `pattern` 검증이 없어 임의 문자열이 프롬프트에 주입될 수 있음. 다른 파라미터(`leverage`, `deal_size`, `rwi_status`, `jurisdiction`)는 모두 정규식으로 허용값을 제한하는데, `industry_type`만 누락.

**증거**:
```python
# spa_analysis.py:194 — pattern 없음
industry_type: str = Form("GENERAL"),

# 비교: 다른 파라미터는 모두 pattern 제한
leverage: str = Form("STRONG", pattern="^(STRONG|WEAK)$"),
deal_size: str = Form("MEDIUM", pattern="^(SMALL|MEDIUM|LARGE)$"),
```

**수정안**: 프롬프트에서 사용하는 산업 유형과 일치하는 Enum 또는 pattern 추가:
```python
industry_type: str = Form("GENERAL", pattern="^(GENERAL|IT_VENTURE|BIO|MANUFACTURING)$"),
```

**심각도 근거**: 프롬프트 인젝션 경로는 아님(시스템 프롬프트의 플레이스홀더 치환이므로), 그러나 잘못된 산업 유형이 분석 품질을 저하시킬 수 있음.

---

#### [R4-M2] response_model 미설정 — OpenAPI 스키마 문서화 부재 — [Major/HIGH] — Priority: P1

**파일**: [spa_analysis.py:183](deal-mgmt/app/routers/spa_analysis.py#L183)

**문제**: `step4_generate_redline` 엔드포인트에 `response_class=StreamingResponse`가 설정되어 있지 않아, Swagger UI에서 응답 형식 정보가 부정확. FastAPI의 `StreamingResponse` 엔드포인트는 `response_class` 또는 `responses` 파라미터로 문서화해야 함.

**수정안**:
```python
@router.post(
    "/step4-redline",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}},
            "description": "Tracked Changes가 적용된 .docx 파일",
        }
    },
)
```

---

#### [R7-H1] _build_char_map 반복 호출 — O(I x P x C) 복잡도 — [High/HIGH] — Priority: P1

**파일**: [redline_engine.py:132-145](deal-mgmt/app/services/redline_engine.py#L132-L145)

**문제**: `_find_target_in_paragraphs()`가 매 이슈마다 모든 문단에 대해 `_build_char_map()`을 호출. 이슈 I개, 문단 P개, 문단당 평균 문자 C개일 때 O(I x P x C). 사전 캐싱으로 O(P x C) 일회성 전처리 + O(I x P) 검색으로 개선 가능.

**현재 코드**:
```python
def _find_target_in_paragraphs(paragraphs, target_text):
    for para in paragraphs:
        merged, char_map = _build_char_map(para)  # 매번 재계산
        # ...
```

**수정안**: `apply_redlines()` 진입 시 전체 문단에 대해 char_map을 사전 계산하여 dict에 캐싱:
```python
# 사전 계산
para_cache = {}
for para in all_paragraphs:
    merged, char_map = _build_char_map(para)
    para_cache[id(para)] = (merged, char_map)
```

**주의**: 이슈 처리 중 Run 분할로 XML 구조가 변경되면 캐시가 stale 상태가 될 수 있음. 이슈 간 캐시 무효화 전략 필요.

---

### P2 — 개선 권장 (점수: 30-59)

#### [R4-Mod1] Content-Disposition 헤더 RFC 순서 — [Moderate/HIGH] — Priority: P2

**파일**: [spa_analysis.py:240-241](deal-mgmt/app/routers/spa_analysis.py#L240-L241)

**문제**: `Content-Disposition` 헤더에서 `filename*` (RFC 5987)이 `filename` 앞에 위치. RFC 6266에 따르면 `filename`(ASCII 폴백)이 먼저, `filename*`(UTF-8)이 뒤에 오는 것이 관례.

**수정안**: 순서 변경 — `filename=` → `filename*=` 순서로.

---

#### [R7-M1] _normalize_text_for_matching 이중 호출 — [Medium/MEDIUM] — Priority: P2

**파일**: [redline_engine.py:132-145](deal-mgmt/app/services/redline_engine.py#L132-L145)

**문제**: `_find_target_in_paragraphs()` 내에서 `target_text`에 대한 정규화가 매 문단 루프마다 반복될 수 있음. 함수 진입 시 한 번만 정규화하면 충분.

---

#### [R3-W1] char_map stale 구조적 취약점 — [Warning/MEDIUM] — Priority: P2

**파일**: [redline_engine.py:190-260](deal-mgmt/app/services/redline_engine.py#L190-L260)

**문제**: `apply_redlines()`에서 이슈를 순차 처리할 때, 이전 이슈의 `_split_run_at()` 및 `_inject_deletion()`/`_inject_insertion()`이 XML 트리를 변형(mutate)함. 이후 이슈의 `_find_target_in_paragraphs()`는 변형된 트리에서 `_build_char_map()`을 재호출하므로 매칭은 정확하지만, 두 이슈의 `original_target_text`가 겹치는 극단적 경우에는 예기치 않은 동작 가능.

**현재 완화 전략**: 매칭 실패 시 skip + comment 삽입으로 안전하게 처리됨.

**권장**: 문서화 수준의 주석 추가 — "이슈 간 XML 변형으로 인한 매칭 순서 의존성 존재" 명시.

---

### P3 — 저우선 (점수: <30)

#### [R7-M2] _repack_docx 메모리 피크 — [Medium/MEDIUM] — Priority: P3

`_repack_docx()`에서 원본 ZIP 전체를 메모리에 유지한 채 새 ZIP도 메모리에 생성. 대용량 DOCX(이미지 다수 포함)에서 메모리 피크 2배. 현 단계에서는 SPA 문서 크기(보통 1~5MB)를 고려하면 실질적 위험 낮음.

#### [R7-L1] infolist() 이중 호출 — [Low/MEDIUM] — Priority: P3

`_repack_docx()`에서 `zf_in.infolist()`를 2회 호출. 변수에 캐싱하면 미미한 개선.

#### [R7-L2] _resolve_run_properties 순차 탐색 — [Low/MEDIUM] — Priority: P3

인접 Run 탐색 시 `list(paragraph)` 변환 후 순차 검색. 문단 내 Run 수가 통상 10~50개이므로 실질적 영향 없음.

#### [R7-L3] re.compile 미사용 — [Low/HIGH] — Priority: P3

`_parse_redline_markup()`에서 정규식을 매 호출마다 컴파일. 모듈 레벨 `re.compile()`으로 전환하면 반복 호출 시 미미한 개선.

#### [R7-L4] _normalize 내 dict 재생성 — [Low/HIGH] — Priority: P3

`_normalize_text_for_matching()` 내 문자 치환 딕셔너리가 매 호출마다 생성됨. 모듈 레벨 상수로 추출 가능.

#### [R3-W2] ZipInfo 메타데이터 미보존 — [Warning/MEDIUM] — Priority: P3

`_repack_docx()`에서 파일 복사 시 `ZipInfo` 메타데이터(압축 방법, 외부 속성 등)를 원본에서 복제하지 않을 수 있음. Word에서 열 때 문제가 되는 경우는 드물지만, 엄격한 호환성을 위해 원본 `ZipInfo` 객체 재사용 권장.

---

### Suggestions (개선 제안)

#### [R6-S1] apply_redlines 성공/실패 요약 로그 추가

`apply_redlines()` 함수 종료 시 "처리 완료: 성공 N건, 실패 M건, 총 이슈 K건" 형태의 요약 로그 추가 권장.

#### [R6-S2] Pydantic 검증 실패 skip 로그에 clause_ref/severity 포함

`spa_analysis_service.py`에서 `RedlineIssueSchema` 검증 실패 시 skip 로그에 `clause_ref`와 `severity` 정보 포함 권장. 현재는 `issue_id`만 로깅.

#### [R6-S3] BadZipFile 예외에 exc_info=True 추가

`spa_analysis.py` 라우터의 `BadZipFile` except 블록에 `exc_info=True` 추가하여 스택 트레이스 보존 권장.

---

## Priority Matrix

### P0 — 즉시 수정 (1건)
1. [R4-C1] [Critical/HIGH]: CORS expose_headers 누락 — main.py (점수: 100)

### P1 — 스프린트 우선 (3건)
1. [R4-M1] [Major/HIGH]: industry_type pattern 미설정 — spa_analysis.py (점수: 70)
2. [R4-M2] [Major/HIGH]: response_model/response_class 미설정 — spa_analysis.py (점수: 70)
3. [R7-H1] [High/HIGH]: _build_char_map 반복 호출 O(IxPxC) — redline_engine.py (점수: 70)

### P2 — 개선 권장 (3건)
1. [R4-Mod1] [Moderate/HIGH]: Content-Disposition RFC 순서 — spa_analysis.py (점수: 40)
2. [R7-M1] [Medium/MEDIUM]: normalize 이중 호출 — redline_engine.py (점수: 24)
3. [R3-W1] [Warning/MEDIUM]: char_map stale 구조적 취약점 — redline_engine.py (점수: 24)

### P3 — 저우선 (6건)
1. [R7-M2] [Medium/MEDIUM]: repack_docx 메모리 피크 — redline_engine.py (점수: 24)
2. [R7-L1] [Low/MEDIUM]: infolist 이중 호출 — redline_engine.py (점수: 6)
3. [R7-L2] [Low/MEDIUM]: resolve_run_properties 순차 탐색 — redline_engine.py (점수: 6)
4. [R7-L3] [Low/HIGH]: re.compile 미사용 — redline_engine.py (점수: 20)
5. [R7-L4] [Low/HIGH]: normalize dict 재생성 — redline_engine.py (점수: 20)
6. [R3-W2] [Warning/MEDIUM]: ZipInfo 메타데이터 미보존 — redline_engine.py (점수: 6)

---

## Methodology

- **Agents**: R3-data-flow, R4-api-contract, R6-observability, R7-performance
- **Files scanned**: 5 (redline_engine.py, spa_analysis.py router, spa_analysis_service.py, spa_analysis.py schema, main.py)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: R3 ↔ R7 (char_map 캐싱/stale 이슈 교차 확인)

## 검증 투명성

### 검증 통계
- 검증한 가설: 18건
- 거부된 가설 (사전 제거): 2건
- 보고된 이슈: 16건
- 거부율: 11%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 1 | lxml thread-safety → run_in_threadpool은 독립 트리 사용, 안전 |
| 범위 외 | 1 | GZip 이중 압축 → nginx 레벨 설정이며 Step 4 코드 범위 아님 |

---

## 이전 리뷰 이력

| 차수 | 날짜 | 관점 | 이슈 수 | 커밋 |
|------|------|------|--------|------|
| 1차 | 03-07 | R1(Security) 전체 | 18건 수정 | `af28e2a` |
| 2차 | 03-07 | R5(Error Handling) | 14건 수정 | `9085bbc` |
| 3차 | 03-07 | R9(Dependencies)+R10(Domain Logic) | 12건 수정 | `c27f0ca` |
| 4차 | 03-07 | R11(Test Quality)+R12(Cognitive Complexity) | 15건 수정 | `bef9506` |
| 5차 | 03-07 | R2(STRIDE)+R6(Observability)+R8(Deploy Safety) | 18건 수정 | `13300a3` |
| **6차** | **03-07** | **R3+R4+R6+R7** | **16건 발견** | *pending* |

> 작성 시각: 2026-03-07 19:36 KST
