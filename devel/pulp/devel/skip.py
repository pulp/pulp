import os

from unittest2 import skipIf


# setting environment variable PULP_RUN_BROKEN_TESTS to any non-empty value
# will cause the tests to not skip broken tests. This is useful for when
# someone is ready to work on fixing the broken tests.
skip_broken = skipIf(not bool(os.environ.get('PULP_RUN_BROKEN_TESTS')),
                     'skipping known-broken test')
