"""Bounded memory caches and per-key request coalescing.

Work happens outside the bookkeeping lock: unrelated keys remain independent.
Completed failures are delivered to current waiters, then removed for retry.
"""
from collections import OrderedDict
from concurrent.futures import Future
from threading import RLock
import time


class SingleFlight:
    def __init__(self, max_pending=128):
        self.max_pending = max_pending
        self._pending = {}
        self._lock = RLock()

    def run(self, key, compute, timeout=None):
        with self._lock:
            future = self._pending.get(key)
            owner = future is None
            if owner:
                future = Future()
                # Bounds bookkeeping even during a burst of distinct requests.
                tracked = len(self._pending) < self.max_pending
                if tracked:
                    self._pending[key] = future
            else:
                tracked = True
        if not owner:
            return future.result(timeout=timeout)
        try:
            value = compute()
        except BaseException as error:
            future.set_exception(error)
            raise
        else:
            future.set_result(value)
            return value
        finally:
            if tracked:
                with self._lock:
                    if self._pending.get(key) is future:
                        self._pending.pop(key, None)


class MemoryCache:
    def __init__(self, max_entries=32, max_bytes=None):
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._entries = OrderedDict()
        self._bytes = 0
        self._lock = RLock()
        self._flight = SingleFlight()

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._bytes = 0

    def get(self, key):
        with self._lock:
            entry = self._entries.get(key)
            if entry and entry[0] > time.monotonic():
                self._entries.move_to_end(key)
                return entry[1]
            if entry:
                self._bytes -= self._entries.pop(key)[2]
            return None

    def get_or_compute(self, key, compute, ttl=300, size=None):
        value = self.get(key)
        if value is not None:
            return value

        def populate():
            value = self.get(key)
            if value is not None:
                return value
            value = compute()
            seconds = ttl(value) if callable(ttl) else ttl
            weight = size(value) if size else 0
            if seconds <= 0 or (self.max_bytes is not None and weight > self.max_bytes):
                return value
            with self._lock:
                previous = self._entries.pop(key, None)
                if previous:
                    self._bytes -= previous[2]
                self._entries[key] = (time.monotonic() + seconds, value, weight)
                self._bytes += weight
                while len(self._entries) > self.max_entries or (self.max_bytes is not None and self._bytes > self.max_bytes):
                    self._bytes -= self._entries.popitem(last=False)[1][2]
            return value

        return self._flight.run(key, populate)
