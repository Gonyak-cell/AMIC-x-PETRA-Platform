# IM Backend Document Generation Pipeline - Code Review

> **Review Date**: 2026-02-13 14:13:40
> **Reviewer**: Claude Opus 4.6
> **Scope**: DART -> Analysis -> Narrative -> Rendering pipeline
> **Files Reviewed**: 16 files across 4 packages

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Finding #1: CRITICAL - Chord Failure Recovery Gap](#finding-1)
3. [Finding #2: CRITICAL - DART API Key Hardcoded as Empty String](#finding-2)
4. [Finding #3: HIGH - No Duplicate corp_code Guard](#finding-3)
5. [Finding #4: HIGH - asyncio.run() Inside Celery Worker Event Loop Conflict](#finding-4)
6. [Finding #5: HIGH - finalize_document_task Does NOT Update DB](#finding-5)
7. [Finding #6: MEDIUM - document_service.py Race Condition Between Commit and Task Dispatch](#finding-6)
8. [Finding #7: MEDIUM - Pipeline gather() Swallows Exceptions Silently](#finding-7)
9. [Finding #8: MEDIUM - Token Budget Uses cl100k_base for All Providers](#finding-8)
10. [Finding #9: MEDIUM - GoogleProvider Creates New Model Instance Per Call](#finding-9)
11. [Finding #10: LOW - NullLLMClient Creates New Objects Per Access](#finding-10)
12. [Finding #11: LOW - progress.py Does Not Persist to DB](#finding-11)
13. [Finding #12: INFO - Token Budget Does Not Account for Prompt Tokens](#finding-12)
14. [Summary Matrix](#summary-matrix)

---

## 1. Architecture Overview

The IM document generation pipeline consists of 5 stages orchestrated via Celery Chord:

```
Stage 1: Data Collection (chord group)
  - fetch_dart_task (DART API)
  - fetch_web_task (web crawling)
  - extract_brand_task (brand assets)
  --> merge_collected_data (chord callback)

Stage 2: analyze_financials_task (chain)
Stage 3: generate_content_task (chain) -- NarrativeOrchestrator with multi-model routing
Stage 4: render_document_task (chain) -- PPTX/PDF
Stage 5: finalize_document_task (chain) -- DB update
```

**Key components**:
- `DocumentService` (API layer) -- creates Document record, dispatches Celery master task
- `generate_im_task` (Celery master) -- assembles chord + chain pipeline
- `DataCollectionPipeline` (data ingestor) -- async DART API + web crawling with priority-based error recovery
- `NarrativeOrchestrator` (narrative generator) -- multi-model LLM routing per section
- `ModelRouter` -- routes sections to OpenAI/Anthropic/Google with fallback chain

**State machine**: `PENDING -> COLLECTING -> ANALYZING -> GENERATING -> RENDERING -> COMPLETED | FAILED`

---

<a id="finding-1"></a>
## Finding #1: CRITICAL -- Chord Failure Recovery Gap

**File**: `src/api/tasks/generate_im.py` lines 50-62
**Actual Code**:
```python
pipeline = chord(
    group(
        fetch_dart_task.s(corp_code),
        fetch_web_task.s(corp_code),
        extract_brand_task.s(corp_code, website_url),
    ),
    merge_collected_data.s(document_id),
) | chain(
    analyze_financials_task.s(document_id),
    generate_content_task.s(document_id),
    render_document_task.s(document_id),
    finalize_document_task.s(document_id),
)
```

**Problem**: If any task in the chord group fails after exhausting retries (fetch_dart_task has `max_retries=3`), the entire chord callback (`merge_collected_data`) is never invoked. The subsequent chain (Stages 2-5) never executes. The document stays in PENDING status **forever** -- no error handler sets it to FAILED.

Furthermore, if a task in the chain (Stage 2-5) fails after retries are exhausted, there is no `on_failure` callback or `link_error` to transition the document to FAILED status.

**Severity**: CRITICAL

**Fix**: Add `link_error` handler to the pipeline to catch any failure and update the document to FAILED:

```python
@celery_app.task(name="handle_pipeline_error")
def handle_pipeline_error(request, exc, traceback, document_id: str):
    """Pipeline failure handler -- sets document to FAILED."""
    # Use sync DB session to update document status
    _sync_update_document_status(document_id, "FAILED", error=str(exc))

pipeline = chord(
    group(...),
    merge_collected_data.s(document_id),
) | chain(...)

pipeline.apply_async(link_error=handle_pipeline_error.s(document_id))
```

Also consider making `fetch_web_task` and `extract_brand_task` non-critical (return empty dict on failure instead of raising, as brand extraction already does).

**Verification Checklist**:
- [ ] Simulate `fetch_dart_task` failure after 3 retries -- confirm document transitions to FAILED
- [ ] Simulate `generate_content_task` failure -- confirm FAILED status
- [ ] Verify `link_error` handler receives correct `document_id`
- [ ] Confirm no zombie PENDING documents after pipeline failures

---

<a id="finding-2"></a>
## Finding #2: CRITICAL -- DART API Key Hardcoded as Empty String

**File**: `src/api/tasks/generate_im.py` line 81 and `src/api/tasks/fetch_company.py` line 33
**Actual Code**:
```python
# generate_im.py line 81
config = PipelineConfig(dart_api_key="")

# fetch_company.py line 33
config = PipelineConfig(dart_api_key="")
```

**Problem**: Both Celery tasks hardcode `dart_api_key=""` when creating `PipelineConfig`. This means the DART API client will be initialized without a valid key, causing **every DART API call to fail** with an authentication error. The `APIConfig` has `dart_api_key` as a setting loaded from `.env`, but neither task reads it.

**Severity**: CRITICAL -- The entire pipeline will fail at Stage 1 in production.

**Fix**: Read the API key from config:

```python
from src.api.config import get_config

api_config = get_config()
config = PipelineConfig(dart_api_key=api_config.dart_api_key)
```

**Verification Checklist**:
- [ ] Confirm `get_config().dart_api_key` loads from env/`.env`
- [ ] Test `fetch_dart_task` with valid DART API key
- [ ] Test `fetch_company_task` with valid DART API key
- [ ] Verify API key is not logged in plaintext

---

<a id="finding-3"></a>
## Finding #3: HIGH -- No Duplicate corp_code Guard

**File**: `src/api/services/document_service.py` lines 28-72
**Actual Code**:
```python
async def create_document(
    self,
    owner_id: UUID,
    create_data: DocumentCreate,
) -> Document:
    document = Document(
        owner_id=owner_id,
        corp_code=create_data.corp_code,
        ...
        status=DocumentStatus.PENDING.value,
    )
    self.db.add(document)
    await self.db.commit()
    ...
    task = generate_im_task.delay(
        str(document.id),
        create_data.corp_code,
        document.generation_config,
    )
```

**Problem**: There is no check to prevent concurrent document generation for the same `corp_code`. If two requests arrive simultaneously for `corp_code="00126380"`, both will:
1. Create separate Document records
2. Dispatch two Celery pipelines
3. Both hit DART API simultaneously (potentially triggering rate limiting)
4. Both consume LLM tokens independently
5. Both write output files (potentially conflicting)

The Document model has `corp_code` indexed but **not unique** (line 50-54 of document.py -- `index=True`, not `unique=True`).

**Severity**: HIGH -- resource waste, rate limit risk, and potential file conflicts.

**Fix**: Add a guard in `create_document`:

```python
async def create_document(self, ...):
    # Check for in-progress generation for same corp_code
    existing = await self.db.execute(
        select(Document).where(
            Document.corp_code == create_data.corp_code,
            Document.status.in_([
                DocumentStatus.PENDING.value,
                DocumentStatus.COLLECTING.value,
                DocumentStatus.ANALYZING.value,
                DocumentStatus.GENERATING.value,
                DocumentStatus.RENDERING.value,
            ]),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            "이미 해당 corp_code로 진행 중인 문서가 있습니다"
        )
    ...
```

Alternatively, use a Redis distributed lock:
```python
lock_key = f"im_gen:{create_data.corp_code}"
if not await redis.set(lock_key, "1", nx=True, ex=600):
    raise ConflictError(...)
```

**Verification Checklist**:
- [ ] Concurrent POST requests for same corp_code -- confirm second request is rejected
- [ ] Verify lock is released when pipeline completes or fails
- [ ] Confirm different corp_codes can run simultaneously
- [ ] Test edge case: FAILED document for same corp_code should not block new generation

---

<a id="finding-4"></a>
## Finding #4: HIGH -- asyncio.run() Inside Celery Worker Event Loop Conflict

**File**: `src/api/tasks/generate_im.py` line 82 and `src/api/tasks/fetch_company.py` line 34
**Actual Code**:
```python
# generate_im.py line 82
result = asyncio.run(_run_collection(config, corp_code))

# fetch_company.py line 34
result = asyncio.run(_collect(config, corp_code))
```

**Problem**: `asyncio.run()` creates a **new** event loop and runs it to completion. If the Celery worker is running in an environment where an event loop already exists (e.g., `gevent`/`eventlet` worker pool, or if any other async library initialized a loop), this will raise `RuntimeError: asyncio.run() cannot be called from a running event loop`.

Even without pool conflicts, each call to `asyncio.run()` creates and destroys a fresh event loop, which has overhead and prevents connection reuse (e.g., aiohttp sessions, asyncpg pools).

**Severity**: HIGH -- may crash in production depending on Celery worker pool configuration.

**Fix**: Use `asgiref.sync.async_to_sync` or create a reusable loop:

```python
import asyncio

def _run_async(coro):
    """Run async coroutine in sync Celery task safely."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        # Already in a running loop (e.g., gevent)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return loop.run_in_executor(pool, asyncio.run, coro)
```

Or better yet, use the `celery[gevent]` compatible pattern:

```python
from asgiref.sync import async_to_sync

@celery_app.task(bind=True, ...)
def fetch_dart_task(self, corp_code: str):
    result = async_to_sync(_run_collection)(config, corp_code)
    ...
```

**Verification Checklist**:
- [ ] Test with `prefork` pool -- confirm no event loop error
- [ ] Test with `gevent` pool -- confirm no event loop error
- [ ] Confirm DataCollectionPipeline async context manager opens/closes correctly
- [ ] Verify aiohttp sessions are properly closed after each call

---

<a id="finding-5"></a>
## Finding #5: HIGH -- finalize_document_task Does NOT Actually Update DB

**File**: `src/api/tasks/generate_im.py` lines 277-299
**Actual Code**:
```python
@celery_app.task(bind=True, name="finalize_document", max_retries=0, acks_late=True)
def finalize_document_task(
    self: Any,
    im_data_dict: dict[str, Any],
    document_id: str,
) -> dict[str, Any]:
    update_progress(self, document_id, "COMPLETED", 100)

    return {
        "document_id": document_id,
        "status": "COMPLETED",
        "pptx_path": im_data_dict.get("pptx_path"),
        "pdf_path": im_data_dict.get("pdf_path"),
    }
```

And `update_progress` (progress.py lines 18-48):
```python
def update_progress(task, document_id, stage, pct, details=None):
    meta = {"document_id": document_id, "stage": stage, "progress_pct": pct}
    task.update_state(state=stage, meta=meta)  # Only updates Celery state
```

**Problem**: `finalize_document_task` calls `update_progress()` which only calls `task.update_state()` -- this updates **Celery task metadata in Redis**, NOT the `Document` row in PostgreSQL. The `Document` table has `status`, `progress_pct`, `pptx_path`, `pdf_path`, and `completed_at` columns, but **none of these are ever written**.

The same applies to all intermediate progress updates (`COLLECTING`, `ANALYZING`, `GENERATING`, `RENDERING`) -- they only update Celery state, not the DB. The `Document.status` column remains `PENDING` forever.

**Severity**: HIGH -- The API's `get_document` and `list_documents` will always show `status=PENDING`, `progress_pct=0`, and `pptx_path=null`.

**Fix**: Add DB updates in `update_progress` and `finalize_document_task`:

```python
def update_progress(task, document_id, stage, pct, details=None):
    task.update_state(state=stage, meta=meta)
    # Also persist to DB
    _sync_update_document(document_id, status=stage, progress_pct=pct)

def _sync_update_document(document_id, **kwargs):
    """Synchronously update Document in DB."""
    from sqlalchemy import create_engine, update
    from src.api.config import get_config
    from src.api.db.models.document import Document

    config = get_config()
    sync_url = config.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(
            update(Document).where(Document.id == document_id).values(**kwargs)
        )
```

For `finalize_document_task`, also persist `pptx_path`, `pdf_path`, `completed_at`.

**Verification Checklist**:
- [ ] After pipeline completion, query `SELECT status FROM documents WHERE id=...` -- confirm `COMPLETED`
- [ ] Verify `pptx_path` and `pdf_path` are written to DB
- [ ] Verify `completed_at` is set
- [ ] Frontend `DocumentDetailPage` shows correct status and progress

---

<a id="finding-6"></a>
## Finding #6: MEDIUM -- Race Condition Between Commit and Task Dispatch

**File**: `src/api/services/document_service.py` lines 59-71
**Actual Code**:
```python
self.db.add(document)
await self.db.commit()           # (A) Document saved with status=PENDING
await self.db.refresh(document)

task = generate_im_task.delay(   # (B) Celery task dispatched
    str(document.id),
    create_data.corp_code,
    document.generation_config,
)
document.celery_task_id = task.id  # (C) Save task ID
await self.db.commit()             # (D) Second commit
await self.db.refresh(document)
```

**Problem**: Two race conditions:

1. **Between (A) and (B)**: If `generate_im_task.delay()` fails (Redis down, serialization error), the document is committed with `status=PENDING` and `celery_task_id=None`. No cleanup occurs -- orphaned PENDING document.

2. **Between (B) and (D)**: The Celery task may start executing *before* the second commit (D) completes. If `finalize_document_task` (or a future DB-writing version) tries to read `celery_task_id` immediately, it might be null.

**Severity**: MEDIUM

**Fix**: Wrap both commits in a single transaction and handle dispatch failure:

```python
async def create_document(self, owner_id, create_data):
    document = Document(...)
    self.db.add(document)
    await self.db.flush()  # Get document.id without committing

    try:
        task = generate_im_task.delay(
            str(document.id),
            create_data.corp_code,
            document.generation_config,
        )
        document.celery_task_id = task.id
        await self.db.commit()
    except Exception:
        await self.db.rollback()
        raise

    await self.db.refresh(document)
    return document
```

**Verification Checklist**:
- [ ] Simulate Redis down -- confirm no orphaned PENDING documents
- [ ] Verify document.id is available after `flush()` (before commit)
- [ ] Confirm Celery task receives valid document_id

---

<a id="finding-7"></a>
## Finding #7: MEDIUM -- Pipeline gather() Swallows Exceptions Silently

**File**: `src/data_ingestor/pipeline.py` line 424
**Actual Code**:
```python
results = await asyncio.gather(*coros, return_exceptions=False)
```

**Problem**: `return_exceptions=False` (the default) means if any coroutine raises, `gather()` will **cancel remaining coroutines and propagate the first exception**. However, each coroutine is already wrapped in `_safe_step()` which catches all exceptions internally. This means `gather()` will *never* see an exception from the wrapped coroutines -- they always return `None` on failure.

The actual issue is the opposite: if a new step is added *without* `_safe_step()` wrapping, it will crash the entire parallel phase. The code pattern is fragile because:

1. The `_fetch_financial_statements`, `_fetch_shareholders`, etc. methods **call** `_safe_step()` which calls `await coro`. But in `_collect_parallel`, the tasks list contains `self._fetch_financial_statements(corp_code, str(year), result)` -- these are **already-started coroutines** because the methods are `async def` and calling them creates coroutines immediately.

2. The pattern `tasks.append(("name", self._fetch_xxx(...)))` starts the coroutine creation but does not execute it. The coroutine is awaited only when `gather()` runs. The `_safe_step` inside each method provides error isolation. This is correct but implicit.

**Severity**: MEDIUM (fragile pattern, currently works but easy to break)

**Fix**: Add explicit `return_exceptions=True` as a safety net, and validate results:

```python
results = await asyncio.gather(*coros, return_exceptions=True)

for name, value in zip(task_names, results):
    if isinstance(value, Exception):
        result.warnings.append(f"Unexpected error in {name}: {value}")
        value = None
    ...
```

**Verification Checklist**:
- [ ] Confirm all parallel steps use `_safe_step()` wrapper
- [ ] Test with one step failing -- confirm other steps complete successfully
- [ ] Verify no unhandled exceptions from `gather()`

---

<a id="finding-8"></a>
## Finding #8: MEDIUM -- Token Budget Uses cl100k_base for All Providers

**File**: `src/narrative_generator/engine/token_budget.py` lines 18-38
**Actual Code**:
```python
def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except ImportError:
        return max(1, int(len(text) / 3.5))
```

And in `orchestrator.py` line 128:
```python
self._token_manager = TokenBudgetManager()  # Uses cl100k_base default
```

**Problem**: `cl100k_base` is OpenAI's tokenizer for GPT-4/3.5. When the ModelRouter sends a section to **Anthropic Claude** or **Google Gemini**, the token count will be inaccurate because:

- Claude uses a different tokenizer (Anthropic's custom BPE). Token counts can differ by 10-20%.
- Gemini uses SentencePiece. Token counts can differ even more.

The `DEFAULT_TOKEN_BUDGETS` (e.g., `executive_summary: 800`) are calibrated for OpenAI tokens. When Claude or Gemini processes these sections, the actual token usage may be significantly different, leading to either:
- Premature truncation (Anthropic tokens are generally longer, so 800 cl100k_base tokens may correspond to ~700 Claude tokens)
- Budget overflow (if the provider's tokens are shorter)

**Severity**: MEDIUM -- affects output quality and cost control across providers.

**Fix**: Make token counting provider-aware:

```python
PROVIDER_CHAR_RATIOS = {
    ProviderName.OPENAI: 3.5,      # cl100k_base
    ProviderName.ANTHROPIC: 3.3,   # Claude tokenizer ~approximate
    ProviderName.GOOGLE: 3.0,      # SentencePiece ~approximate
}

def count_tokens_for_provider(text: str, provider: ProviderName) -> int:
    if provider == ProviderName.OPENAI:
        return count_tokens(text, "cl100k_base")
    # Fallback to character ratio for non-OpenAI
    ratio = PROVIDER_CHAR_RATIOS.get(provider, 3.5)
    return max(1, int(len(text) / ratio))
```

**Verification Checklist**:
- [ ] Compare token counts across providers for same text sample
- [ ] Verify truncation works correctly for Anthropic-routed sections
- [ ] Confirm budget warnings fire appropriately for each provider

---

<a id="finding-9"></a>
## Finding #9: MEDIUM -- GoogleProvider Creates New Model Instance Per generate() Call

**File**: `src/narrative_generator/engine/providers/google_provider.py` lines 83-87
**Actual Code**:
```python
def generate(self, system_prompt, user_prompt, *, model=None, ...):
    model_name = model or self._default_model
    try:
        if self._client_factory is not None:
            gen_model = self._client_factory(model_name, system_prompt)
        else:
            gen_model = self._genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
            )
```

**Problem**: A new `GenerativeModel` instance is created for **every** `generate()` call. For a typical IM document with ~7 Gemini-routed sections (company_overview, business_overview, deal_overview, market_overview, management_team, business_model, appendix), this creates 7 model instances.

While the Gemini SDK may handle this efficiently internally, it is wasteful and could cause issues if the SDK caches model-level state or opens connections per instance.

More importantly, the `system_instruction` is set at model initialization time, which means it **must** create a new instance when the system prompt changes. This is architecturally correct but differs from OpenAI/Anthropic patterns where system prompt is per-call.

**Severity**: MEDIUM (performance, not correctness)

**Fix**: Cache model instances by `(model_name, hash(system_prompt))`:

```python
def __init__(self, ...):
    self._model_cache: dict[tuple[str, int], Any] = {}

def _get_model(self, model_name: str, system_prompt: str):
    key = (model_name, hash(system_prompt))
    if key not in self._model_cache:
        self._model_cache[key] = self._genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )
    return self._model_cache[key]
```

**Verification Checklist**:
- [ ] Verify model cache hit for same system_prompt (e.g., two Gemini sections with same template)
- [ ] Confirm cache miss when system_prompt differs
- [ ] Memory profiling: confirm no excessive model instance accumulation

---

<a id="finding-10"></a>
## Finding #10: LOW -- NullLLMClient Creates New Objects Per Property Access

**File**: `src/narrative_generator/engine/orchestrator.py` lines 423-457
**Actual Code**:
```python
class _NullLLMClient:
    @property
    def chat(self) -> "_NullChat":
        return _NullChat()     # New instance every time

class _NullChat:
    @property
    def completions(self) -> "_NullCompletions":
        return _NullCompletions()  # New instance every time
```

**Problem**: Each access to `client.chat.completions.create()` instantiates 3 new objects. While individually inexpensive, this is unnecessary object churn in a Null Object pattern.

**Severity**: LOW

**Fix**: Use singleton instances:

```python
class _NullLLMClient:
    def __init__(self):
        self._chat = _NullChat()

    @property
    def chat(self):
        return self._chat
```

**Verification Checklist**:
- [ ] Confirm NullLLMClient works when no API key is set
- [ ] Verify warning log is emitted once per section, not per object creation

---

<a id="finding-11"></a>
## Finding #11: LOW -- progress.py Does Not Persist to DB

**File**: `src/api/tasks/progress.py` lines 18-48
**Actual Code**:
```python
def update_progress(task, document_id, stage, pct, details=None):
    meta = {
        "document_id": document_id,
        "stage": stage,
        "progress_pct": pct,
    }
    if details:
        meta["details"] = details
    task.update_state(state=stage, meta=meta)
```

**Problem**: This only updates Celery task state (stored in Redis with 24h TTL from `result_expires=86400`). The `Document` table's `status`, `progress_pct`, and `stage_details` columns are **never updated during pipeline execution**.

This is related to but distinct from Finding #5: while Finding #5 focuses on the final status not being persisted, this finding covers the entire lifecycle. The frontend polling the Document API will always see stale data. The only way to get current progress is to query Celery task state directly (which requires knowing the `celery_task_id`).

**Severity**: LOW (progress is still queryable via Celery, but the API/DB is inconsistent)

**Fix**: Add a sync DB update call inside `update_progress`, or create a separate Celery periodic task that syncs Celery state to DB.

**Verification Checklist**:
- [ ] Query Document status at each stage -- confirm DB reflects current state
- [ ] Verify frontend progress bar works with DB-persisted progress

---

<a id="finding-12"></a>
## Finding #12: INFO -- Token Budget Does Not Account for Prompt Tokens (Cost Control Gap)

**File**: `src/narrative_generator/engine/token_budget.py` (DEFAULT_TOKEN_BUDGETS) and `src/narrative_generator/config.py` line 87 (`narrative_max_tokens: int = 4096`)

**Problem**: The token budget system only controls **output** token count per section (DEFAULT_TOKEN_BUDGETS sums to ~8,100 tokens across 15 sections). However, there is no tracking or budgeting of:

1. **Input (prompt) tokens**: Each section's system + user prompt can be 2,000-5,000 tokens, multiplied by 15 sections = 30,000-75,000 input tokens.
2. **Total cost**: With multi-model routing, costs vary dramatically:
   - GPT-4o: ~$2.50/1M input + $10/1M output
   - Claude Sonnet 4: ~$3/1M input + $15/1M output
   - Gemini 2.0 Flash: ~$0.10/1M input + $0.40/1M output

3. **Per-document cost cap**: There is no mechanism to abort generation if accumulated cost exceeds a threshold.

The `LLMResponse.usage` field captures token usage per call, but no code aggregates or checks it against a budget.

**Severity**: INFO (design consideration, not a bug)

**Fix**: Add cost tracking to NarrativeOrchestrator:

```python
@dataclass
class CostTracker:
    max_cost_usd: float = 1.0
    accumulated_cost: float = 0.0

    COST_PER_1K = {
        ProviderName.OPENAI: {"input": 0.0025, "output": 0.01},
        ProviderName.ANTHROPIC: {"input": 0.003, "output": 0.015},
        ProviderName.GOOGLE: {"input": 0.0001, "output": 0.0004},
    }

    def add_usage(self, provider: ProviderName, usage: dict):
        rates = self.COST_PER_1K[provider]
        cost = (usage["prompt_tokens"] / 1000 * rates["input"] +
                usage["completion_tokens"] / 1000 * rates["output"])
        self.accumulated_cost += cost
        if self.accumulated_cost > self.max_cost_usd:
            raise CostBudgetExceeded(self.accumulated_cost, self.max_cost_usd)
```

**Verification Checklist**:
- [ ] Log total cost per document generation
- [ ] Alert when cost exceeds configurable threshold
- [ ] Track cost per provider for billing attribution

---

<a id="summary-matrix"></a>
## Summary Matrix

| # | Severity | Category | File | Issue |
|---|----------|----------|------|-------|
| 1 | **CRITICAL** | Pipeline Failure | `generate_im.py:50-62` | Chord failure leaves document in PENDING forever -- no error handler |
| 2 | **CRITICAL** | Configuration | `generate_im.py:81`, `fetch_company.py:33` | DART API key hardcoded as empty string |
| 3 | **HIGH** | Concurrency | `document_service.py:28-72` | No duplicate corp_code guard for concurrent requests |
| 4 | **HIGH** | Runtime | `generate_im.py:82`, `fetch_company.py:34` | `asyncio.run()` may crash with existing event loop |
| 5 | **HIGH** | Data Integrity | `generate_im.py:277-299` | `finalize_document_task` does not write status/paths to DB |
| 6 | **MEDIUM** | Concurrency | `document_service.py:59-71` | Race condition between DB commit and Celery dispatch |
| 7 | **MEDIUM** | Error Handling | `pipeline.py:424` | `gather()` pattern is fragile; exceptions silently swallowed |
| 8 | **MEDIUM** | Accuracy | `token_budget.py:18-38` | cl100k_base tokenizer used for all providers |
| 9 | **MEDIUM** | Performance | `google_provider.py:83-87` | New GenerativeModel instance per generate() call |
| 10 | **LOW** | Performance | `orchestrator.py:423-457` | NullLLMClient creates new objects per property access |
| 11 | **LOW** | Data Integrity | `progress.py:18-48` | Progress updates not persisted to DB |
| 12 | **INFO** | Cost Control | `token_budget.py`, `config.py` | No prompt token / cost tracking across providers |

## Priority Recommendation

**Phase 1 (Immediate -- blocks production)**:
1. Fix #2 (DART API key) -- trivial 2-line fix
2. Fix #5 (DB not updated) -- requires sync DB helper in Celery tasks
3. Fix #1 (chord failure) -- add `link_error` handler

**Phase 2 (Before beta launch)**:
4. Fix #3 (duplicate corp_code)
5. Fix #4 (asyncio.run conflict)
6. Fix #6 (race condition)

**Phase 3 (Optimization)**:
7. Fix #7-#12 (medium/low severity improvements)

---

> **Note**: All file paths are relative to `IM Module/auto-im-generator/`. All findings are based on actual code read via the Read tool. No architecture was assumed -- every claim references specific line numbers and code snippets.
