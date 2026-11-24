import asyncio

from dashboard import cache


def _run(coro):
    return asyncio.run(coro)


def test_cache_hits_isolates_and_cleans_up_locks():
    cache.clear()
    calls = []

    @cache.cached(ttl=60)
    async def fn(session, period):
        calls.append(period)
        if period == "bad":
            raise ValueError("bad period")
        return {"period": period}

    async def scenario():
        first = await fn(None, "week")
        first["period"] = "mutated"  # must not leak into the cached copy
        assert (await fn(None, "week")) == {"period": "week"}
        assert calls == ["week"]  # second call was a cache hit

        # Concurrent callers share one computation.
        cache.clear()
        calls.clear()
        await asyncio.gather(*(fn(None, "month") for _ in range(5)))
        assert calls == ["month"]

        # A failing call stores nothing and must not leave its lock behind.
        for _ in range(3):
            try:
                await fn(None, "bad")
            except ValueError:
                pass
        assert cache._locks == {}
        assert not any("bad" in k[2] for k in cache._store)

    _run(scenario())


def test_cache_store_is_bounded():
    cache.clear()

    @cache.cached(ttl=60)
    async def fn(session, period):
        return period

    async def scenario():
        for i in range(cache._MAX_ENTRIES * 2):
            await fn(None, f"custom:{i}")
        assert len(cache._store) <= cache._MAX_ENTRIES

    _run(scenario())


if __name__ == "__main__":
    test_cache_hits_isolates_and_cleans_up_locks()
    test_cache_store_is_bounded()
