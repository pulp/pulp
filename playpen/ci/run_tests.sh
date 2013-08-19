#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to clean up after a build & test suite has been run in order to return the server to the
# pre build/test execution state.

echo "Running the tests"
set -x
rm -rf $WORKSPACE/test
mkdir $WORKSPACE/test


cd $WORKSPACE/pulp
python run-tests.py  --with-xunit --xunit-file ../test/pulpTest.xml
# nosetests platform/test/unit/ --with-xunit --xunit-file platformTest.xml --process-timeout=360
# nosetests builtins/test/unit/ --with-xunit --xunit-file builtinsTest.xml --process-timeout=360
# nosetests pulp_devel/test/unit/ --with-xunit --xunit-file builtinsTest.xml --process-timeout=360

cd $WORKSPACE/pulp_rpm
python run-tests.py
# nosetests pulp_rpm/test/unit/ --with-xunit --xunit-file puppetTest.xml --process-timeout=360

cd $WORKSPACE/pulp_puppet
bash run-tests.sh
# nosetests  pulp_puppet_common/test/unit/ --with-xunit --xunit-file puppetTest.xml --process-timeout=360
# nosetests  pulp_puppet_extensions_admin/test/unit/ --with-xunit --xunit-file puppetTest.xml --process-timeout=360
# nosetests  pulp_puppet_extensions_consumer/test/unit/ --with-xunit --xunit-file puppetTest.xml --process-timeout=360
# nosetests  pulp_puppet_handlers/test/unit/ --with-xunit --xunit-file puppetTest.xml --process-timeout=360
# nosetests  pulp_puppet_plugins/test/unit/ --with-xunit --xunit-file puppetTest.xml --process-timeout=360