from __future__ import annotations

import asyncio

from app.tasks.persistent_async import PersistentAsyncRunner, run_on_shared_celery_loop


async def _capture_loop_id() -> int:
    await asyncio.sleep(0)
    return id(asyncio.get_running_loop())


async def _raise_error() -> None:
    await asyncio.sleep(0)
    raise RuntimeError("boom")


def test_persistent_async_runner_reuses_the_same_event_loop() -> None:
    runner: PersistentAsyncRunner[int] = PersistentAsyncRunner("test-persistent-async")
    try:
        first = runner.run(_capture_loop_id())
        second = runner.run(_capture_loop_id())
    finally:
        runner.shutdown()

    assert first == second


def test_persistent_async_runner_surfaces_coroutine_errors() -> None:
    runner: PersistentAsyncRunner[None] = PersistentAsyncRunner("test-persistent-async-error")
    try:
        try:
            runner.run(_raise_error())
        except RuntimeError as exc:
            assert str(exc) == "boom"
        else:
            raise AssertionError("Expected RuntimeError from coroutine")
    finally:
        runner.shutdown()


def test_shared_celery_async_runner_reuses_the_same_event_loop() -> None:
    first = run_on_shared_celery_loop(_capture_loop_id())
    second = run_on_shared_celery_loop(_capture_loop_id())

    assert first == second
