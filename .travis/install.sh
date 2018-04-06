#!/usr/bin/env sh
set -v

# dev_requirements should not be needed for testing; don't install them to make sure
pip install "Django<=DJANGO_MAX"
pip install -r test_requirements.txt
pushd common/ && pip install -e . && popd
pushd pulpcore/ && pip install -e . && popd
pushd plugin/ && pip install -e .  && popd

export COMMIT_MSG=$(git log --format=%B -n 1 HEAD)
export PULP_FILE_PR_NUMBER=$(echo $COMMIT_MSG | grep -oP 'Required\ PR:\ https\:\/\/github\.com\/pulp\/pulp_file\/pull\/(\d+)' | awk -F'/' '{print $7}')
export PULP_SMASH_PR_NUMBER=$(echo $COMMIT_MSG | grep -oP 'Required\ PR:\ https\:\/\/github\.com\/PulpQE\/pulp-smash\/pull\/(\d+)' | awk -F'/' '{print $7}')
echo $COMMIT_MSG
echo $PULP_FILE_PR_NUMBER
echo $PULP_SMASH_PR_NUMBER
if [ -z $PULP_FILE_PR_NUMBER ]; then
  export PULP_FILE_SHA='master';
else
  export PULP_FILE_SHA=$(http https://api.github.com/repos/pulp/pulp_file/pulls/$PULP_FILE_PR_NUMBER | jq -r '.merge_commit_sha')
fi

if [ -z $PULP_SMASH_PR_NUMBER ]; then
  PULP_SMASH_SHA='master';
else
  export PULP_SMASH_SHA=$(http https://api.github.com/repos/PulpQE/pulp-smash/pulls/$PULP_SMASH_PR_NUMBER | jq -r '.merge_commit_sha')
fi

if [ $TEST = 'pulp_file' ]; then
  pip install git+https://github.com/pulp/pulp_file.git@$PULP_FILE_SHA#egg=pulp_file
fi

pip install pytest git+https://github.com/PulpQE/pulp-smash.git@$PULP_SMASH_SHA#egg=pulp-smash
