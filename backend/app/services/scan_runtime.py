from __future__ import annotations

import asyncio


_refresh_event: asyncio.Event | None = None
_refresh_event_loop: asyncio.AbstractEventLoop | None = None


def _get_refresh_event() -> asyncio.Event:
    global _refresh_event, _refresh_event_loop

    loop = asyncio.get_running_loop()
    if _refresh_event is None or _refresh_event_loop is not loop:
        _refresh_event = asyncio.Event()
        _refresh_event_loop = loop
    return _refresh_event


def request_scan_refresh() -> None:
    try:
        event = _get_refresh_event()
    except RuntimeError:
        return
    event.set()


async def wait_for_refresh_or_timeout(timeout_seconds: int) -> bool:
    event = _get_refresh_event()
    try:
        await asyncio.wait_for(event.wait(), timeout=max(timeout_seconds, 1))
        return True
    except asyncio.TimeoutError:
        return False
    finally:
        event.clear()