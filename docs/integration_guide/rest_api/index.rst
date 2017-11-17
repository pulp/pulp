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

.. swaggerv2doc:: http://localhost:8000/api/v3/docs/?format=openapi