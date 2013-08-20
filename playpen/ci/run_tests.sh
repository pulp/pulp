#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to clean up after a build & test suite has been run in order to return the
# server to the pre build/test execution state.

echo "Running the tests"
set -x
rm -rf $WORKSPACE/test
mkdir $WORKSPACE/test


cd $WORKSPACE/pulp
python run-tests.py  --with-xunit --xunit-file ../test/pulpTest.xml

cd $WORKSPACE/pulp_rpm
python run-tests.py  --with-xunit --xunit-file ../test/pulp_rpmTest.xml

cd $WORKSPACE/pulp_puppet
python run-tests.py  --with-xunit --xunit-file ../test/pulp_puppetTest.xml
