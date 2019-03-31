import asyncio
from asyncio import Future
from twisted.internet.defer import ensureDeferred, Deferred


def as_future(d: Deferred):
    return d.asFuture(asyncio.get_event_loop())


def as_deferred(f: Future):
    return Deferred.fromFuture(asyncio.ensure_future(f))
