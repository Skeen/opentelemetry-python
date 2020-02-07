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
import operator
import typing

from opentelemetry import propagators, trace
from opentelemetry.ext.asgi.version import __version__  # noqa
from opentelemetry.trace.status import Status, StatusCanonicalCode
from opentelemetry.ext.wsgi import http_status_to_canonical_code

_HTTP_VERSION_PREFIX = "HTTP/"


def get_header_from_scope(
    scope: dict, header_name: str
) -> typing.List[str]:
    headers = scope.get('headers')
    return [
        value.decode('utf8') for (key,value) in headers
        if key.decode('utf8') == header_name
    ]


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
        span_name = get_default_span_name(scope)

        with self.tracer.start_as_current_span(span_name, parent_span, kind=trace.SpanKind.SERVER, attributes=collect_request_attributes(scope)) as connection_span:
            print("connection", connection_span.get_context())
            async def wrapped_receive():
                with self.tracer.start_as_current_span(span_name + " (unknown-receive)") as receive_span:
                    print("wrapped_receive", receive_span.get_context())
                    payload = await receive()
                    if payload['type'] == "websocket.receive":
                        receive_span.set_attribute("http.status_code", 200)
                        receive_span.set_status(Status(http_status_to_canonical_code(200)))
                        receive_span.set_attribute("http.status_text", payload['text'])
                    receive_span.update_name(span_name + " (" + payload['type'] + ")")
                    receive_span.set_attribute('type', payload['type'])
                return payload

            async def wrapped_send(payload):
                with self.tracer.start_as_current_span(span_name + " (unknown-send)") as send_span:
                    print("wrapped_send", send_span.get_context())
                    if payload['type'] == "http.response.start":
                        status_code = payload['status']
                        try:
                            status_code = int(status_code)
                        except ValueError:
                            send_span.set_status(
                                Status(
                                    StatusCanonicalCode.UNKNOWN,
                                    "Non-integer HTTP status: " + repr(status_code),
                                )
                            )
                        else:
                            send_span.set_attribute("http.status_code", status_code)
                            send_span.set_status(Status(http_status_to_canonical_code(status_code)))
                    elif payload['type'] == "websocket.send":
                        send_span.set_attribute("http.status_code", 200)
                        send_span.set_status(Status(http_status_to_canonical_code(200)))
                        send_span.set_attribute("http.status_text", payload['text'])

                    send_span.update_name(span_name + " (" + payload['type'] + ")")
                    send_span.set_attribute('type', payload['type'])
                    await send(payload)
            await self.asgi(scope)(wrapped_receive, wrapped_send)
