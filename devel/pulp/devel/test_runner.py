# -*- coding: utf-8 -*-
"""
This module is to contain the helper functions used by the test runners in pulp, pulp_rpm, &
pulp_puppet
"""

import argparse
import os
import subprocess
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'pulp.server.webservices.settings'


# From: http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python/377028#377028
def which(program):
    import os

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def run_tests(packages, tests_all_platforms, tests_non_rhel5,
              flake8_paths=None, flake8_exclude=None):
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
    :param flake8_paths: paths that should be checked with flake8
    :type flake8_paths: list of str
    :param flake8_exclude: list of paths that should be ignored during the flake8 check
    :type  flake8_exclude: list
    :return: the exit code from nosetests
    :rtype:  integer
    """

    # Test to make sure the necessary executables exist
    if which('flake8') is None:
        print 'flake8 not found or is not executable! Please correct before running tests.'
        exit(2)
    if which('nosetests') is None:
        print 'nosetests not found or is not executable! Please correct before running tests.'
        exit(2)

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
    flake8_exit_code = 0
    if sys.version_info >= (2, 6):
        # make sure we test everything
        args.extend(tests_non_rhel5)

        # Check the files for coding conventions
        if flake8_paths:
            # Ignore E401: multiple imports on one line
            flake8_default_exclude = '--exclude=.ropeproject,docs,playpen,*/build/*'
            if flake8_exclude:
                flake8_exclude = flake8_default_exclude + ',%s' % ','.join(flake8_exclude)
            else:
                flake8_exclude = flake8_default_exclude
            flake8_command = ['flake8', '--max-line-length=100', '--ignore=E401', flake8_exclude]
            flake8_command.extend(flake8_paths)
            if arguments.verbose:
                print 'Running {flake8}'.format(flake8=' '.join(flake8_command))
            else:
                print 'Running flake8'
            flake8_exit_code = subprocess.call(flake8_command)

    else:
        args.extend(['-e', 'server'])
        args.extend(['-e', 'plugins'])

    args.extend(tests_all_platforms)

    if arguments.failfast:
        args.extend(['-x'])
        if flake8_exit_code:
            return flake8_exit_code
    if arguments.verbose:
        args.extend(['-v'])
    if arguments.with_xunit:
        args.extend(['--with-xunit', '--process-timeout=360'])
    if arguments.xunit_file:
        args.extend(['--xunit-file', '../test/' + arguments.xunit_file])

    if arguments.verbose:
        print 'Running {tests}'.format(tests=' '.join(args))
    else:
        print "Running Unit Tests"
    # Call the test process, and return its exit code
    return subprocess.call(args) or flake8_exit_code
