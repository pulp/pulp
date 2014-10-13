Exception Handling
==================

.. _exception_handling:

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
* **error** *(object)* - error details and nested errors.  :ref:`error_details`

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
  "http_status": 404,
  "error": {
            "code": "PLP0009",
            "description": "Missing resource(s): foo",
            "data": {"resource": "foo"},
            "sub_errors": []
            }
 }


.. _error_details:

Error Details
=============
Pulp is moving to provide more programmatically useful results when errors occur.
One of the primary ways we are doing this is through the new "error" object. This object
will be included in the body for all JSON calls that have errors.  The error object will contain
the following fields.

* **code** *(string)* - A 7 digit string uniquely identifying this error.  The first 3 characters
                        are [A-Z] and identify the project in which the error occurred.
                        Today the possible values are "PLP", "PPT", and "RPM" for the pulp, pulp_puppet
                        and pulp_rpm projects.  The last 4 digits are numeric to identify the error.
* **description** *(string)* - A user readable message describing the error that occurred
* **data** *(object)* - The data specific to this error.  Each error code specifies the fields that
                        will be included in this object.
* **sub_errors** *(array)* - An array of error details objects that contributed to this error.

Example serialized error details::

 {
  "code": "PLP0018",
  "description": "Duplicate resource: foo",
  "data": {"resource_id": "foo"},
  "sub_errors": []
 }


Error Codes
===========
Pulp Error codes should be segmented.  The following segments have been established
* PLP0000-PLP0999 - General Server Errors (and legacy PulpException errors)
* PLP1000-PLP2999 - Validation errors
