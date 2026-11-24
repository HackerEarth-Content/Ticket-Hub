"""Short-TTL in-process cache for dashboard read functions.

Data only changes when the scheduler's sync runs (every few minutes), so
recomputing the same period's numbers for every viewer / every refresh is
wasted DB work -- and it's the first thing that falls over as viewers grow.

Decorate a read function whose first argument is the DB session:

    @cached()
    async def get_thing(session, period): ...

The session is deliberately NOT part of the key. Auth happens in the route's
dependencies *before* these functions run, so a cached value is only ever
served to a caller who already passed the same check.

Concurrent callers asking for the same key share ONE computation (per-key
lock), so a burst of viewers can't stampede the database. Results are
deep-copied in and out so callers can't mutate what's cached.

Single-process only, like the scheduler (see core/scheduler.py): with several
workers each keeps its own copy, which is still correct, just less shared.
"""

from __future__ import annotations

import asyncio
import copy
import functools
import time

DEFAULT_TTL_SECONDS = 60
_MAX_ENTRIES = 512  # custom date ranges make the key space unbounded

_store: dict[tuple, tuple[float, object]] = {}
_locks: dict[tuple, asyncio.Lock] = {}


def clear() -> None:
    """Drop everything -- called after each sync so fresh data shows at once."""
    _store.clear()
    _locks.clear()


def _evict_if_full() -> None:
    if len(_store) < _MAX_ENTRIES:
        return
    now = time.monotonic()
    for key in [k for k, (expires, _) in _store.items() if expires <= now]:
        _store.pop(key, None)
        _locks.pop(key, None)
    # Still full of live entries: drop the oldest-expiring half.
    if len(_store) >= _MAX_ENTRIES:
        for key, _ in sorted(_store.items(), key=lambda kv: kv[1][0])[
            : _MAX_ENTRIES // 2
        ]:
            _store.pop(key, None)
            _locks.pop(key, None)


def cached(ttl: float = DEFAULT_TTL_SECONDS):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(session, *args, **kwargs):
            key = (fn.__module__, fn.__qualname__, args, tuple(sorted(kwargs.items())))

            def _fresh():
                hit = _store.get(key)
                if hit and hit[0] > time.monotonic():
                    return hit
                return None

            if hit := _fresh():
                return copy.deepcopy(hit[1])
            async with _locks.setdefault(key, asyncio.Lock()):
                if hit := _fresh():  # someone else computed it while we waited
                    return copy.deepcopy(hit[1])
                result = await fn(session, *args, **kwargs)
                _evict_if_full()
                _store[key] = (time.monotonic() + ttl, result)
            return copy.deepcopy(result)

        return wrapper

    return decorator
