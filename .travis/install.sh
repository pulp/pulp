#!/usr/bin/env sh
set -v

# dev_requirements should not be needed for testing; don't install them to make sure
pip install "Django<=$DJANGO_MAX"
pip install -r test_requirements.txt
pushd common/ && pip install -e . && popd
pushd pulpcore/ && pip install -e . && popd
pushd plugin/ && pip install -e .  && popd

export COMMIT_MSG=$(git show HEAD^2 -s)
export PULP_FILE_PR_NUMBER=$(echo $COMMIT_MSG | grep -oP 'Required\ PR:\ https\:\/\/github\.com\/pulp\/pulp_file\/pull\/(\d+)' | awk -F'/' '{print $7}')
export PULP_SMASH_PR_NUMBER=$(echo $COMMIT_MSG | grep -oP 'Required\ PR:\ https\:\/\/github\.com\/PulpQE\/pulp-smash\/pull\/(\d+)' | awk -F'/' '{print $7}')

if [ -z $PULP_FILE_PR_NUMBER ]; then
  pip install git+https://github.com/pulp/pulp_file.git#egg=pulp_file
else
  export PULP_FILE_SHA=$(curl https://api.github.com/repos/pulp/pulp_file/pulls/$PULP_FILE_PR_NUMBER | jq -r '.merge_commit_sha')
  cd ../
  git clone https://github.com/pulp/pulp_file.git
  cd pulp_file
  git fetch origin +refs/pull/$PULP_FILE_PR_NUMBER/merge
  git checkout $PULP_FILE_SHA
  pip install -e .
  cd ../pulp
fi

if [ -z $PULP_SMASH_PR_NUMBER ]; then
  pip install git+https://github.com/PulpQE/pulp-smash.git#egg=pulp-smash
else
  export PULP_SMASH_SHA=$(curl https://api.github.com/repos/PulpQE/pulp-smash/pulls/$PULP_SMASH_PR_NUMBER | jq -r '.merge_commit_sha')
  cd ../
  git clone https://github.com/PulpQE/pulp-smash.git
  cd pulp-smash
  git fetch origin +refs/pull/$PULP_SMASH_PR_NUMBER/merge
  git checkout $PULP_SMASH_SHA
  pip install -e .
  cd ../pulp
fi
