---
paths:
  - "kiis/**/*.py"
  - "im/**/*.py"
---
# Async Patterns (비동기 프로그래밍 규칙)

## asyncio 기본
- `async def` + `await` 일관 사용
- 동기 함수에서 비동기 호출 금지 (`asyncio.run()` 남용 금지)
- CPU-bound 작업: `asyncio.to_thread()` 또는 `ProcessPoolExecutor`

## Semaphore (동시성 제한)
```python
sem = asyncio.Semaphore(10)

async def fetch_with_limit(url: str) -> Response:
    async with sem:
        return await client.get(url)
```

## httpx 타임아웃
```python
timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
async with httpx.AsyncClient(timeout=timeout) as client:
    response = await client.get(url)
```

## asyncio.gather 규칙
```python
# 반드시 return_exceptions=True
results = await asyncio.gather(
    fetch_company(code1),
    fetch_company(code2),
    return_exceptions=True,
)
for result in results:
    if isinstance(result, Exception):
        logger.error(f"Failed: {result}")
```

## 리소스 정리
```python
# async with 패턴 사용
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# 또는 try/finally
client = httpx.AsyncClient()
try:
    response = await client.get(url)
finally:
    await client.aclose()
```

## 금지 패턴
- `asyncio.sleep()` 을 polling 대용으로 사용 금지
- bare `asyncio.create_task()` → 반드시 참조 유지
- `loop.run_until_complete()` 사용 금지 (이미 이벤트 루프 실행 중)
- 동기 `requests` 라이브러리 사용 금지 → `httpx` 사용
- 동기 파일 I/O (`open()`) → `aiofiles` 사용

## APScheduler (KIIS)
- `AsyncIOScheduler` 사용
- Job 중복 방지: `replace_existing=True`
- 에러 시 재시도 로직 포함
- 스케줄러 종료 시 graceful shutdown
