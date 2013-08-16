#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to clean up after a build & test suite has been run in order to return the server to the
# pre build/test execution state.

echo "Cleaning up after the build"
set -x
env
export WORKSPACE=$HOME/workspace/$JOB_NAME
cd $WORKSPACE
sudo pip-python uninstall -y Pulp-Platform
sudo pip-python uninstall -y pulp-devel
sudo pip-python uninstall -y pulp-rpm
sudo pip-python uninstall -y pulp-rpm-plugins
sudo pip-python uninstall -y pulp-puppet-common
sudo pip-python uninstall -y pulp-puppet-extensions-admin
sudo pip-python uninstall -y pulp-puppet-extensions-consumer
sudo pip-python uninstall -y pulp-puppet-handlers
sudo pip-python uninstall -y pulp-puppet-plugins
sudo pip-python uninstall -y nectar

sudo python pulp/pulp-dev.py -U
sudo python pulp_rpm/pulp-dev.py -U
sudo python pulp_puppet/pulp-dev.py -U

sudo rm -Rf /etc/pulp/*
sudo rm -Rf /var/lib/pulp/*
sudo rm -Rf /usr/lib/pulp/*
sudo rm -Rf /etc/pki/pulp/*

#Don't remove the source directories so they can be inspected if something goes wrong
# sudo rm -Rf pulp
# sudo rm -Rf pulp_rpm
# sudo rm -Rf pulp_puppet
# sudo rm -Rf nectar

echo "Finished cleaning up."
