.. _pulpcore: https://github.com/PulpQE/pulp-smash/tree/master/pulp_smash/tests/pulp3/pulpcore
.. _file: https://github.com/PulpQE/pulp-smash/tree/master/pulp_smash/tests/pulp3/file
.. _pulp-smash: https://github.com/PulpQE/pulp-smash/


.. _continuous-integration:

Continuous Integration
======================

New code is highly encouraged to have basic unit tests that demonstrate its functionality. A Pull
Request that has failing unit tests cannot be merged.

The unit tests for `pulpcore` are in `pulpcore/tests <https://github.com/pulp/pulp/tree/3.0-dev/pulpcore/tests>`_.

Integration tests for new code should be added to a separate project called pulp-smash_. A Pull
Request that has failing pulp-smash tests cannot be merged.

The integration tests for the REST API live in the pulpcore_ folder and the Plugin API is tested
with tests in the file_ folder.


Requiring Other Pull Requests
-----------------------------

When a Pull Request breaks any pulp-smash test, it is the responsibility of the author to fix the
failing tests. Fixing the tests may require an update of the `pulp_file` plugin in addition to
any `pulp-smash` changes. Once additional Pull Requests for `pulp-smash` and `pulp_file` have been
created, links to them can be specified in the commit message of the Pull Request against `pulp`::

    Required PR: https://github.com/PulpQE/pulp-smash/pull/1234
    Required PR: https://github.com/pulp/pulp_file/pull/2345

This will allow the PR against pulp to run against the Pull Requests for pulp-smash and pulp_file.

Attention and care must be given to merging PRs that require other Pull Requests. Before merging,
all required PRs should be ready to merge--meaning that all tests/checks should be passing, the code
review requirements should be met, etc. When merging, the PR along with its required PRs should all
be merged at the same time. This is necessary to ensure that test breakages don't block other PRs.
