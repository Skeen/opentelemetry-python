OpenTelemetry celery integration
================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-celery.svg
   :target: https://pypi.org/project/opentelemetry-ext-celery/

This library allows tracing celery tasks made by the popular `celery <http://www.celeryproject.org/>`_ library.

Installation
------------

::

     pip install opentelemetry-ext-celery

Usage
-----

.. code-block:: python

    import celery
    import opentelemetry.ext.celery
    from opentelemetry.trace import tracer_source

    opentelemetry.ext.celery.enable(tracer_source())
    result = add.delay(2,3).get()

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
