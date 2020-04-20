import asyncio
from asyncio import Future
from twisted.internet.defer import ensureDeferred, Deferred
from typing import Awaitable


def as_future(d: Deferred) -> Future:
    return d.asFuture(asyncio.get_event_loop())


def as_deferred(f: Awaitable) -> Deferred:
    return Deferred.fromFuture(asyncio.ensure_future(f))
