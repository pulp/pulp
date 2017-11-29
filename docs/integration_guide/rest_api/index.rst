REST API Reference
==================

.. toctree::
   :maxdepth: 3

   authentication


pulpcore REST API
-----------------

Each instance of Pulp hosts dynamically generated API documentation located at `http://pulpserver/api/v3/docs/`
if `drf_openapi` is installed. This documentation includes the installed pulp plugin endpoints and is a more
complete version of the API documented below.

.. note::

    `drf_openapi` package on PyPi is currently broken. Please install it from source::

    $ pip3 install -e git+https://github.com/limdauto/drf_openapi.git@54d24fb#egg=drf_openapi


.. swaggerv2doc:: http://localhost:8000/api/v3/docs/?format=openapi