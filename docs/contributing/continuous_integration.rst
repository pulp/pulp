.. _tests: https://github.com/pulp/pulp/blob/3.0-dev/tests/
.. _pulpcore: https://github.com/PulpQE/pulp-smash/tree/master/pulp_smash/tests/pulp3/pulpcore
.. _file: https://github.com/PulpQE/pulp-smash/tree/master/pulp_smash/tests/pulp3/file
.. _pulp-smash: https://github.com/PulpQE/pulp-smash/


.. _continuous-integration:

Continuous Integration
======================

New code is highly encouraged to have basic unit tests that demonstrate its functionality. A Pull
Request that has failing unit tests cannot be merged.

The unit tests for both `pulpcore` and `pulpcore-plugin` live in the tests_ folder.

Integration tests for new code should be added to a separate project called pulp-smash_. A Pull
Request that has failing pulp-smash tests cannot be merged.

The integration tests for the REST API live in the pulpcore_ folder and the Plugin API is tested
with tests in the file_ folder.

When a Pull Request breaks any pulp-smash test, it is the responsibility of the author to fix the
failing tests. Fixing the tests may require an update of the `pulp_file` plugin in addition to
any `pulp-smash` changes. Once additional Pull Requests for `pulp-smash` and `pulp_file` have been
created, links to them can be specified in the commit message of the Pull Request against `pulp`::

    Required PR: https://github.com/PulpQE/pulp-smash/pull/1234
    Required PR: https://github.com/pulp/pulp_file/pull/2345
