#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to clean up after a build & test suite has been run in order to return the
# server to the pre build/test execution state.

echo "Cleaning up after the build"
set -x
cd $WORKSPACE

pip list | grep pulp | cut -f1 -d"=" | while read line
do
  sudo pip-python uninstall -y $line
done
sudo pip-python uninstall -y nectar

sudo pip-python uninstall -y Pulp-Platform
sudo pip-python uninstall -y nectar

sudo python pulp/pulp-dev.py -U
sudo python pulp_rpm/pulp-dev.py -U
sudo python pulp_puppet/pulp-dev.py -U

sudo rm -Rf /etc/pulp/*
sudo rm -Rf /var/lib/pulp/*
sudo rm -Rf /usr/lib/pulp/*
sudo rm -Rf /etc/pki/pulp/*

echo "Finished cleaning up."
