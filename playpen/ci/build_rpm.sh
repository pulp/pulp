#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to do a test build of the pulp RPMs
# to verify any changes to the specif files.

echo "Test Building the RPMs"
set -x
# Jenkins isn't setting the workspace properly on slave nodes so resetting it here
WORKSPACE="$(readlink -f $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../../../)"
OS_NAME=$(lsb_release -si)
OS_VERSION=$(lsb_release -sr | cut -f1 -d.)

cd ${WORKSPACE}
mkdir -p tito

#function that takes a directory as an argument and runs the setup steps within that directory
function build_rpm {
    pushd $1
    tito build --rpm --test --output ${WORKSPACE}/tito
    popd
}

build_rpm 'pulp'
build_rpm 'pulp_rpm'
build_rpm 'pulp_puppet'

if [ "$OS_NAME" == "RedHatEnterpriseServer" ] && [ "$OS_VERSION" == "5" ]; then
    # Lot's of the stuff isn't built on rhel 5
    echo "Skipping non RHEL5 compliant packages"
else
    build_rpm 'pulp/nodes'
fi
