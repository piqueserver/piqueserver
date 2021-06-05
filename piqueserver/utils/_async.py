import asyncio
from asyncio import Future
from twisted.internet.defer import ensureDeferred, Deferred
from twisted.internet import reactor
from typing import Awaitable, Optional, Callable


def as_future(d: Deferred) -> Future:
    return d.asFuture(asyncio.get_event_loop())


def as_deferred(f: Awaitable) -> Deferred:
    return Deferred.fromFuture(asyncio.ensure_future(f))


class EndCall:
    """a call that can be rescheduled while in the future"""
    def __init__(self, protocol, delay: int, func: Callable, *arg, **kw) -> None:
        self.protocol = protocol
        protocol.end_calls.append(self)
        self.delay = delay
        self.func = func
        self.arg = arg
        self.kw = kw
        self.call = None  # type: Optional[Deferred]
        self._active = True

    def set(self, value: Optional[float]) -> None:
        if value is None:
            if self.call is not None:
                self.call.cancel()
                self.call = None
        elif value is not None:
            value = value - self.delay
            if value <= 0.0:
                self.cancel()
            elif self.call:
                # In Twisted==18.9.0, reset() is broken when using
                # AsyncIOReactor
                # self.call.reset(value)
                self.call.cancel()
                self.call = reactor.callLater(value, self.fire)
            else:
                self.call = reactor.callLater(value, self.fire)

    def fire(self):
        self.call = None
        self.cancel()
        self.func(*self.arg, **self.kw)

    def cancel(self) -> None:
        self.set(None)
        self.protocol.end_calls.remove(self)
        self._active = False

    def active(self) -> bool:
        return self._active and (self.call and self.call.active())
