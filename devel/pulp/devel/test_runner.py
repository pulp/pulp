# -*- coding: utf-8 -*-
"""
This module is to contain the helper functions used by the test runners in pulp, pulp_rpm, &
pulp_puppet
"""

import subprocess
import sys
import argparse


def run_tests(packages, tests_all_platforms, tests_non_rhel5):
    """
    Method used by each of the pulp projects to execute their unit & coverage tests
    This method ensures that the arguments that are used by all of them are consistent.

    :param packages: List of packages that should have test coverage data collected
    :type packages: list of str
    :param tests_all_platforms: List of test directories to inspect for tests that are run on
                                all platforms
    :type tests_all_platforms: list of str
    :param tests_non_rhel5: List of test directories to inspect for tests that are run on
                            all platforms except rhel 5
    :type tests_non_rhel5: list of str

    :return: the exit code from nosetests 
    :rtype:  integer
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--xunit-file')
    parser.add_argument('--with-xunit', action='store_true')
    parser.add_argument('--enable-coverage', action='store_true', default=False)
    parser.add_argument('--with-xcoverage', action='store_true')
    parser.add_argument('--cover-min-percentage', type=int, nargs=1)
    parser.add_argument('--xcoverage-file')
    parser.add_argument('-x', '--failfast', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')

    arguments = parser.parse_args()

    args = [
        'nosetests',
    ]

    if arguments.enable_coverage:
        if arguments.with_xcoverage:
            args.extend(['--with-xcoverage'])
        else:
            args.extend(['--with-coverage'])

        if arguments.xcoverage_file:
            args.extend(['--xcoverage-file', arguments.xcoverage_file])

        if arguments.cover_min_percentage:
            args.extend(['--cover-min-percentage', str(arguments.cover_min_percentage[0])])

        args.extend(['--cover-html',
                     '--cover-erase',
                     '--cover-package',
                     ','.join(packages)])

    # don't run the server or plugins tests in RHEL5.
    if sys.version_info >= (2, 6):
        args.extend(tests_non_rhel5)
    else:
        args.extend(['-e', 'server'])
        args.extend(['-e', 'plugins'])

    args.extend(tests_all_platforms)

    if arguments.failfast:
        args.extend(['-x'])
    if arguments.verbose:
        args.extend(['-v'])
    if arguments.with_xunit:
        args.extend(['--with-xunit', '--process-timeout=360'])
    if arguments.xunit_file:
        args.extend(['--xunit-file', '../test/' + arguments.xunit_file])

    # Call the test process, and return its exit code
    return subprocess.call(args)
