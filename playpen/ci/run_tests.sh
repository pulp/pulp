#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to run the test suite for each project and save the results so the build
# server can parse them.

echo "Running the tests"
set -x
# Jenkins isn't setting the workspace properly on slave nodes so resetting it here
WORKSPACE="$(readlink -f $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../../../)"

rm -rf ${WORKSPACE}/test
mkdir -p ${WORKSPACE}/test
rm -rf ${WORKSPACE}/coverage
mkdir -p ${WORKSPACE}/coverage

cd ${WORKSPACE}/pulp
python ./run-tests.py --enable-coverage --with-xunit --xunit-file ../test/pulp_test.xml --with-xcoverage --xcoverage-file ../coverage/pulp_coverage.xml

cd ${WORKSPACE}/pulp_rpm
python ./run-tests.py --enable-coverage --with-xunit --xunit-file ../test/pulp_rpm_test.xml --with-xcoverage --xcoverage-file ../coverage/pulp_rpm_coverage.xml

cd ${WORKSPACE}/pulp_puppet
python ./run-tests.py --enable-coverage --with-xunit --xunit-file ../test/pulp_puppet_test.xml --with-xcoverage --xcoverage-file ../coverage/pulp_puppet_coverage.xml
