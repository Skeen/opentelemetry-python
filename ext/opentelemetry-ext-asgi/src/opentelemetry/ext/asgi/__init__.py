# Copyright 2019, OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
The opentelemetry-ext-wsgi package provides a WSGI middleware that can be used
on any WSGI framework (such as Django / Flask) to track requests timing through
OpenTelemetry.
"""

import typing

from opentelemetry import propagators, trace
from opentelemetry.ext.asgi.version import __version__  # noqa
from opentelemetry.trace.status import Status, StatusCanonicalCode

_HTTP_VERSION_PREFIX = "HTTP/"


def get_header_from_scope(
    scope: dict, header_name: str
) -> typing.List[str]:
    print(header_name)
    headers = scope.get('headers')
    print("headers", headers)
    string_headers = list(map(
        lambda tup: tuple(map(lambda x: x.decode('utf8'), tup)), headers
    ))
    print("string_headers", string_headers)
    filtered_headers = list(filter(
        lambda tup: tup[0] == header_name, string_headers
    ))
    print("filtered_headers", filtered_headers)
    result = list(map(
        lambda tup: tup[1], filtered_headers
    ))
    print("parent_header", result)
    return result


def get_default_span_name(scope):
    return scope.get("path", "/")


def collect_request_attributes(scope):
    """Collects HTTP request attributes, and returns a dictionary to be used as span creation attributes."""

    result = {
        "component": scope.get("type"),
        "http.method": scope.get("method"),
        "http.server_name": ":".join(map(str, scope.get("server"))),
        "http.scheme": scope.get("scheme"),
        "http.host": scope.get("server")[0],
        "http.port": scope.get("server")[1],
    }

    target = scope.get("path")
    if target is not None:
        result["http.target"] = target

    flavor = scope.get("http_version")
    if flavor:
        result["http.flavor"] = flavor

    return result


class OpenTelemetryMiddleware:
    """The ASGI application middleware.

    Args:
        asgi: The ASGI application callable to forward requests to.
    """
    def __init__(self, asgi):
        self.asgi = asgi
        self.tracer = trace.tracer_source().get_tracer(__name__, __version__)

    async def __call__(self, scope, receive, send):
        parent_span = propagators.extract(get_header_from_scope, scope)
        print("parent_span", parent_span)
        span_name = get_default_span_name(scope)

        span = self.tracer.start_span(
            span_name,
            parent_span,
            kind=trace.SpanKind.SERVER,
            attributes=collect_request_attributes(scope),
        )

        try:
            with self.tracer.use_span(span):
                await self.asgi(scope)(receive, send)
                span.end()
        except:  # noqa
            # TODO Set span status (cf. https://github.com/open-telemetry/opentelemetry-python/issues/292)
            span.end()
            raise
