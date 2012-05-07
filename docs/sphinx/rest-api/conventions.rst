Conventions
===========

Exception Handling
------------------

In the event of a failure (non-200 status code), the returned body will be a
JSON document describing the error. This applies to all method calls; for
simplicity, the individual method documentation will not repeat this information.
The document will contain the following:

* **http_status** *(number)* - HTTP status code describing the error.
* **href** *(string)* - Currently unused.
* **error_message** *(string)* - Description of what caused the error; may be empty but will
  be included in the document.
* **exception** *(string)* - Message extracted from the exception if one occurred on
  the server; may be empty if the error was due to a data validation instead of an exception.
* **traceback** *(string)* - Traceback of the exception if one occurred; may be empty for the same reasons as exception.

All methods have the potential to raise a 500 response code in the event of an
unexpected server-side error. Again, for simplicity that has not been listed on
a per method basis but applies across all calls.

Example serialized exception::

 {
  "exception": null,
  "traceback": null,
  "_href": "/pulp/api/v2/repositories/missing-repo/",
  "resource_id": "missing-repo",
  "error_message": "Missing resource: missing-repo",
  "http_request_method": "DELETE",
  "http_status": 404
 }


Date and Time Formats
---------------------

Pulp utilizes the iso8601 date and time formats. All date/time reporting or
setting is done using iso8601 strings.

