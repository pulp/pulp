#!/usr/bin/env bash

# If this was triggered by a scratch build, use that repo url
if [ -z "$NEW_REPO" ]; then
    REPO=${PULP_REPOSITORY}
else
    REPO=${NEW_REPO}
fi

BUILDTIME=$(date +%s)
cd ${WORKSPACE}/pulp/playpen/deploy/

EXIT=0
python deploy-environment.py --config config/jenkins/${target_platform}-config.yml \
    --deployed-config ${BUILDTIME}.json --repo ${REPO} --test-branch ${TEST_BRANCH} || EXIT=$?

python run-integration-tests.py --config ${BUILDTIME}.json || EXIT=$?

python cleanup-environment.py --config ${BUILDTIME}.json || EXIT=$?
