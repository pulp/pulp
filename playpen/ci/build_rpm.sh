#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to configure pulp on a server after the source has been
# extracted from source control

echo "Setting up after source control extract"
set -x
# Jenkins isn't setting the workspace properly on slave nodes so resetting it here
cd $WORKSPACE
mkdir -p tito

#function that takes a directory as an argument and runs the setup steps within that directory
function build_rpm {
    pushd $1
    tito build --rpm --test --output $WORKSPACE/tito
    popd
}

build_rpm 'pulp'
build_rpm 'pulp_rpm'
build_rpm 'pulp_puppet'

if [ "$OS_NAME" == "RedHat" ] && [ "$OS_VERSION" == "5" ]; then
    # Lot's of the stuff isn't built on rhel 5
    echo "Nectar is not installed on RHEL 5"
else
    build_rpm 'pulp/nodes'
fi
