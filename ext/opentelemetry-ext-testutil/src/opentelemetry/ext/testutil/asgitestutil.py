import io
import unittest
from importlib import reload
import asyncio
from asgiref.testing import ApplicationCommunicator

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerSource, export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

_MEMORY_EXPORTER = None


def setup_testing_defaults(scope):
    scope.update({
        'client': ('127.0.0.1', 32767),
        'headers': [],
        'http_version': '1.0',
        'method': 'GET',
        'path': '/',
        'query_string': b'',
        'scheme': 'http',
        'server': ('127.0.0.1', 80),
        'type': 'http'
    })


class AsgiTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global _MEMORY_EXPORTER  # pylint:disable=global-statement
        trace_api.set_preferred_tracer_source_implementation(
            lambda T: TracerSource()
        )
        tracer_source = trace_api.tracer_source()
        _MEMORY_EXPORTER = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(_MEMORY_EXPORTER)
        tracer_source.add_span_processor(span_processor)

    @classmethod
    def tearDownClass(cls):
        reload(trace_api)

    def setUp(self):
        self.memory_exporter = _MEMORY_EXPORTER
        self.memory_exporter.clear()

        self.scope = {}
        setup_testing_defaults(self.scope)
        self.communicator = None

    def tearDown(self):
        if self.communicator:
            asyncio.get_event_loop().run_until_complete(
                self.communicator.wait()
            )

    def seed_app(self, app):
        self.communicator = ApplicationCommunicator(app, self.scope)

    def send_input(self, payload):
        asyncio.get_event_loop().run_until_complete(
            self.communicator.send_input(payload)
        )
        
    def send_default_request(self):
        self.send_input({'type': 'http.request', 'body': b''})

    def get_output(self):
        output = asyncio.get_event_loop().run_until_complete(
            self.communicator.receive_output(0)
        )
        return output

    def get_all_output(self):
        outputs = []
        while True:
            try:
                outputs.append(self.get_output())
            except asyncio.TimeoutError as e:
                break
        return outputs
