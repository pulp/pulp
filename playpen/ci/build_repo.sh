#!/usr/bin/env bash
# This script expects to run within the Jenkins Build Process
# The purpose of the script is to do a scratch build in koji
# and put the repository on a remote server.
REPO_HOST="pulp-infra@satellite6.lab.eng.rdu2.redhat.com"
REPO_LOCATION="/var/www/html/pulp/${KOJI_BUILD_STREAM}/${KOJI_BUILD_VERSION}/"
BUILD_HISTORY=30

echo "Running builder.py"
set -x
set -e

# Jenkins isn't setting the workspace properly on slave nodes so resetting it here
WORKSPACE="$(readlink -f $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../../../)"
OS_NAME=$(lsb_release -si)
OS_VERSION=$(lsb_release -sr | cut -f1 -d.)

cd ${WORKSPACE}

# Make a scratch build,  dump it on the server, and clean up
python pulp/rel-eng/builder.py $KOJI_BUILD_VERSION $KOJI_BUILD_STREAM --scratch
mv mash ${BUILD_ID}
ssh ${REPO_HOST} mkdir -p ${REPO_LOCATION}
scp -r ${BUILD_ID} ${REPO_HOST}:${REPO_LOCATION}
rm -r ${BUILD_ID}

# Run a script to link the new build and remove old builds
ssh ${REPO_HOST} << ENDSSH
cd ${REPO_LOCATION}

# Link the latest build
rm latest
ln -s ${BUILD_ID} latest

# Remove all but the last BUILD_HISTORY builds
if [ "$(ls -l | wc -l)" -ge "$BUILD_HISTORY" ] ; then
        (ls -t | head -n ${BUILD_HISTORY} ; ls) | sort | uniq -u | xargs rm -r
fi
ENDSSH
