#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to extract the source tree from github.

echo "Setting up after source control extract"
set -x
env
# Jenkins isn't setting the workspace properly on slave nodes so resetting it here
export WORKSPACE=$HOME/workspace/$JOB_NAME
cd $WORKSPACE

#delete the directories if they exist already
sudo rm -Rf pulp
sudo rm -Rf pulp_rpm
sudo rm -Rf pulp_puppet
sudo rm -Rf nectar

#Clone the workspaces
git clone git://github.com/pulp/nectar.git      -b $PULP_NECTAR_BRANCH
git clone git://github.com/pulp/pulp.git        -b $PULP_GIT_PULP_BRANCH
git clone git://github.com/pulp/pulp_rpm.git    -b $PULP_GIT_PULP_RPM_BRANCH
git clone git://github.com/pulp/pulp_puppet.git -b $PULP_GIT_PULP_PUPPET_BRANCH

#Make sure we have the latest version
pushd nectar
git pull
popd
pushd pulp
git pull
popd
pushd pulp_rpm
git pull
popd
pushd pulp_puppet
git pull
popd