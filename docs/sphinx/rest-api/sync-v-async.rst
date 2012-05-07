Synchronous and Asynchronous Calls
==================================

Overview
--------

Pulp uses an advanced task queueing system that detects and avoids concurrent
operations that conflict. It utilizes this system to manage all REST API calls.
This means that any REST API will return one of three responses:

* A success response. This is usually in the form of a 200 OK or a 201 CREATED.
* A postponed response. This is in the form of a 202 ACCEPTED.
* A conflict response. This is in the form of a 409 CONFLICT.

The success response means that no conflicts were detected and the REST call
proceeded. This is what is typically expected from a REST API call.

A postponed response means that a conflict was detected, but the call can be
executed at a later point in time. The call will be carried out by an
asynchronous *task*. The response body is a serialized **call report**
(see below) that contains metadata about the call, its progress, and resolution
as well as an href that can be used to poll for updates to this information.

A conflict response means that a conflict was detected that causes the call to
be unserviceable now or at any point in the future. The body of this response
is Pulp's standard exception format, including the *reasons* for the response.

Serialization
-------------

A 202 ACCEPTED response returns a **call report** response body that includes
the following fields:

* _href - uri path to retrieve subsequent call reports for this task.
* response - a response from Pulp's tasking system: accepted, postponed, or rejected
* reasons - a list of reasons for postponed or rejected responses
* state - the current state of the task
* task_id - the unique id of the task that is executing the asynchronous call
* job_id - the unique id of the job the task is a part of
* schedule_id - the unique id of the schedule if the call is scheduled
* progress - arbitrary progress information, usually in the form of an object
* result - the return value of the call, if any
* exception - the error exception value, if any
* traceback - the resulting traceback if an exception was raised
* start_time - the time the call started executing
* finish_time - the time the call stopped executing
* tags - arbitrary tags useful for looking up the call report

