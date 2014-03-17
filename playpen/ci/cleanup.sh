#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to clean up after a build & test suite has been run in order to return the
# server to the pre build/test execution state.

echo "Cleaning up after the build"
set -x
# Jenkins isn't setting the workspace properly on slave nodes so resetting it here
WORKSPACE="$(readlink -f $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../../../)"
cd ${WORKSPACE}

pip freeze | grep "pulp\|gofer\|nectar" | cut -f1 -d"=" | while read line
do
  sudo pip uninstall -y ${line}
done

sudo python pulp/pulp-dev.py -U
sudo python pulp_rpm/pulp-dev.py -U
sudo python pulp_puppet/pulp-dev.py -U

sudo rm -Rf /etc/pulp/*
sudo rm -Rf /var/lib/pulp/*
sudo rm -Rf /usr/lib/pulp/*
sudo rm -Rf /etc/pki/pulp/*

echo "Finished cleaning up."
