#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to configure pulp on a server after the source has been
# extracted from source control

echo "Setting up after source control extract"
set -x
# Jenkins isn't setting the workspace properly on slave nodes so resetting it here
env
cd $WORKSPACE

#function that takes a directory as an argument and runs the setup steps within that directory
function setup {
    pushd $1

    # Find all the setup.py files and execute run pip install in those directories
    find . -name setup.py | while read SETUP_FILE; do
        SETUP_DIR=`dirname "${SETUP_FILE}"`
        sudo pip-python install -e ${SETUP_DIR}
    done

    sudo python pulp-dev.py -I
    popd
}

if [ "$OS_NAME" == "RedHat" ] && [ "$OS_VERSION" == "5" ]; then
    # don't install nectar on RHEL 5
    echo "Nectar is not installed on RHEL 5"
else
    setup 'nectar'
fi

setup 'pulp'
setup 'pulp_rpm'
setup 'pulp_puppet'
