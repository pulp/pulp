#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to configure pulp on a server after the source has been
# extracted from source control

echo "Setting up after source control extract"
set -x
# Jenkins isn't setting the workspace properly on slave nodes so resetting it here
env
cd $WORKSPACE

if [ "$OS_NAME" == "RedHat" ] && [ "$OS_VERSION" != "5" ]; then
    pushd nectar
    sudo pip-python install -e .
    popd
fi

pushd pulp
sudo pip-python install -e platform/src/
sudo pip-python install -e pulp_devel/
sudo pip-python install -e nodes/common
sudo pip-python install -e nodes/parent
sudo pip-python install -e nodes/child
sudo python pulp-dev.py -I
popd
pushd pulp_rpm
sudo pip-python install -e pulp_rpm/src/
sudo pip-python install -e plugins/
sudo python pulp-dev.py -I
popd
pushd pulp_puppet
sudo pip-python install -e pulp_puppet_common/
sudo pip-python install -e pulp_puppet_extensions_admin/
sudo pip-python install -e pulp_puppet_extensions_consumer/
sudo pip-python install -e pulp_puppet_handlers/
sudo pip-python install -e pulp_puppet_plugins/
sudo python pulp-dev.py -I
popd