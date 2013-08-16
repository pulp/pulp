#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to run the test suite for each project and save the results so the build
# server can parse them.

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
