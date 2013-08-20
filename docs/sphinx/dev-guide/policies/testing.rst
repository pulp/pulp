Testing
=======

Conventions
-----------

Unit tests are found under the ``test/unit`` directory in each subproject.

Unit tests may use the database but should not make any other external
connections, such as to an external repository or the message bus.

Test cases are required for all submitted pull requests.


Python Libraries
----------------

The Pulp project uses the ``mock`` library as its mocking framework. More
information on the framework can be found here: http://pypi.python.org/pypi/mock

Tests should not introduce any extra libraries in order to keep the test
environment light-weight.


Testing Utilities
-----------------

Each project contains a number of testing utility modules under the ``test/unit``
directory. Of particular interest is the module named ``base.py``. This module
provides a number of test case base classes that are used to simulate the
necessary state of the different Pulp components. For example, in the platform,
base classes are provided that set up the state for client tests
(``PulpClientTests``) or REST API tests (``PulpWebserviceTests``).
Applicability and usage information can be found in the docstrings for each
class.

The above base classes should only be used in the event they are needed. The
added setup and tear down time should be avoided in the event that those
features are not needed, in which case simply subclassing ``unittest.TestCase``
is preferred.


Compatibility
-------------

Each unit test directory contains a subdirectory called ``server``. This
distinction is due to the fact that the Pulp client must be
Python 2.4 compatible whereas the server need only be Python 2.6 compatible.
To keep the project's continuous integration tests against 2.4 from failing,
the server tests are not run in those environments. More information on supported
versions can be found on our :doc:`compatibility` page.

This structure is only present in git repositories that have not yet been
migrated into a multiple Python package format. In the latter case, the division
between server and client code is expressed by the packages themselves and thus
this construct is unnecessary.


Coverage
--------

Each Pulp git repository contains a script named ``run-tests.py``. This script
will run all of the unit tests for that repository and generate coverage reports.
The python ``coverage`` library is used to produce the reports and must be
installed before running that script. An HTML version of the coverage report
is created in the git repository root under ``coverage/index.html``.
