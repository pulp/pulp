#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to run the test suite for each project and save the results so the build
# server can parse them.

echo "Running the tests"
set -x
rm -rf $WORKSPACE/test
mkdir $WORKSPACE/test


cd $WORKSPACE/pulp
python ./run-tests.py  --with-xunit --xunit-file ../test/pulp_test.xml

cd $WORKSPACE/pulp_rpm
python ./run-tests.py  --with-xunit --xunit-file ../test/pulp_rpm_test.xml

cd $WORKSPACE/pulp_puppet
python ./run-tests.py  --with-xunit --xunit-file ../test/pulp_puppet_test.xml
