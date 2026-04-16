from __future__ import annotations

import atexit
import asyncio
import threading
from collections.abc import Awaitable
from typing import Generic, TypeVar

_T = TypeVar("_T")


class PersistentAsyncRunner(Generic[_T]):
    """Run coroutines on a single long-lived event loop thread."""

    def __init__(self, thread_name: str) -> None:
        self._thread_name = thread_name
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._lock = threading.Lock()
        atexit.register(self.shutdown)

    def _bootstrap_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        try:
            loop.run_forever()
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self._loop is not None and self._loop.is_running():
                return self._loop

            self._ready.clear()
            self._thread = threading.Thread(
                target=self._bootstrap_loop,
                name=self._thread_name,
                daemon=True,
            )
            self._thread.start()

        self._ready.wait()
        assert self._loop is not None
        return self._loop

    def run(self, coro: Awaitable[_T]) -> _T:
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    def shutdown(self) -> None:
        with self._lock:
            loop = self._loop
            thread = self._thread
            self._loop = None
            self._thread = None

        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
