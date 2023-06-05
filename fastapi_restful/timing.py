"""
Based on https://github.com/steinnes/timing-asgi.git

The middleware from this module is intended for use during both development and production,
but only reports timing data at the granularity of individual endpoint calls.

For more detailed performance investigations (during development only, due to added overhead),
consider using the coroutine-aware profiling library `yappi`.
"""
from __future__ import annotations

import os
import psutil
import time
from collections.abc import Callable
from fastapi import FastAPI
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match, Mount
from starlette.types import Scope
from typing import Any

TIMER_ATTRIBUTE = "__fastapi_utils_timer__"


def add_timing_middleware(
    app: FastAPI, record: Callable[[str], None] | None = None, prefix: str = "", exclude: str | None = None
) -> None:
    """
    Adds a middleware to the provided `app` that records timing metrics using the provided `record` callable.

    Typically `record` would be something like `logger.info` for a `logging.Logger` instance.

    The provided `prefix` is used when generating route names.

    If `exclude` is provided, timings for any routes containing `exclude`
    as an exact substring of the generated metric name will not be logged.
    This provides an easy way to disable logging for routes

    The `exclude` will probably be replaced by a regex match at some point in the future. (PR welcome!)
    """
    metric_namer = _MetricNamer(prefix=prefix, app=app)

    @app.middleware("http")
    async def timing_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
        metric_name = metric_namer(request.scope)
        with _TimingStats(metric_name, record=record, exclude=exclude) as timer:
            setattr(request.state, TIMER_ATTRIBUTE, timer)
            response = await call_next(request)
        return response


def record_timing(request: Request, note: str | None = None) -> None:
    """
    Call this function at any point that you want to display elapsed time during the handling of a single request

    This can help profile which piece of a request is causing a performance bottleneck.

    Note that for this function to succeed, the request should have been generated by a FastAPI app
    that has had timing middleware added using the `fastapi_utils.timing.add_timing_middleware` function.
    """
    timer = getattr(request.state, TIMER_ATTRIBUTE, None)
    if timer is not None:
        if not isinstance(timer, _TimingStats):
            raise ValueError("Timer should be of an instance of TimingStats")
        timer.emit(note)
    else:
        raise ValueError("No timer present on request")


class _TimingStats:
    """
    This class tracks and records endpoint timing data.

    Should be used as a context manager; on exit, timing stats will be emitted.

    name:
        The name to include with the recorded timing data
    record:
        The callable to call on generated messages. Defaults to `print`, but typically
        something like `logger.info` for a `logging.Logger` instance would be preferable.
    exclude:
        An optional string; if it is not None and occurs inside `name`, no stats will be emitted
    """

    def __init__(
        self, name: str | None = None, record: Callable[[str], None] | None = None, exclude: str | None = None
    ) -> None:
        self.name = name
        self.record = record or print

        self.process: psutil.Process = psutil.Process(os.getpid())
        self.start_time: float = 0
        self.start_cpu_time: float = 0
        self.end_cpu_time: float = 0
        self.end_time: float = 0
        self.silent: bool = False

        if self.name is not None and exclude is not None and (exclude in self.name):
            self.silent = True

    def start(self) -> None:
        self.start_time = time.time()
        self.start_cpu_time = self._get_cpu_time()

    def take_split(self) -> None:
        self.end_time = time.time()
        self.end_cpu_time = self._get_cpu_time()

    @property
    def time(self) -> float:
        return self.end_time - self.start_time

    @property
    def cpu_time(self) -> float:
        return self.end_cpu_time - self.start_cpu_time

    def __enter__(self) -> _TimingStats:
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.emit()

    def emit(self, note: str | None = None) -> None:
        """
        Emit timing information, optionally including a specified note
        """
        if not self.silent:
            self.take_split()
            cpu_ms = 1000 * self.cpu_time
            wall_ms = 1000 * self.time
            message = f"TIMING: Wall: {wall_ms:6.1f}ms | CPU: {cpu_ms:6.1f}ms | {self.name}"
            if note is not None:
                message += f" ({note})"
            self.record(message)

    def _get_cpu_time(self) -> float:
        """
        Generates the cpu time to report. Adds the user and system time, following the implementation from timing-asgi
        """
        resources = self.process.cpu_times()
        # add up user time and system time
        return resources[0] + resources[1]


class _MetricNamer:
    """
    This class generates the route "name" used when logging timing records.

    If the route has `endpoint` and `name` attributes, the endpoint's module and route's name will be used
    (along with an optional prefix that can be used, e.g., to distinguish between multiple mounted ASGI apps).

    By default, in FastAPI the route name is the `__name__` of the route's function (or type if it is a callable class
    instance).

    For example, with prefix == "custom", a function defined in the module `app.crud` with name `read_item`
    would get name `custom.app.crud.read_item`. If the empty string were used as the prefix, the result would be
    just "app.crud.read_item".

    For starlette.routing.Mount instances, the name of the type of `route.app` is used in a slightly different format.

    For other routes missing either an endpoint or name, the raw route path is included in the generated name.
    """

    def __init__(self, prefix: str, app: FastAPI):
        if prefix:
            prefix += "."
        self.prefix = prefix
        self.app = app

    def __call__(self, scope: Scope) -> str:
        """
        Generates the actual name to use when logging timing metrics for a specified ASGI Scope
        """
        route = None
        for r in self.app.router.routes:
            if r.matches(scope)[0] == Match.FULL:
                route = r
                break
        if hasattr(route, "endpoint") and hasattr(route, "name"):
            name = f"{self.prefix}{route.endpoint.__module__}.{route.name}"  # type: ignore
        elif isinstance(route, Mount):
            name = f"{type(route.app).__name__}<{route.name!r}>"
        else:
            name = str(f"<Path: {scope['path']}>")
        return name
