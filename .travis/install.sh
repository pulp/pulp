#!/usr/bin/env sh
set -v

# temporary workaround until a newer RQ release is available
pip install git+https://github.com/rq/rq.git@3133d94b58e59cb86e8f4677492d48b2addcf5f8

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
  cd ../
  git clone https://github.com/pulp/pulp_file.git
  cd pulp_file
  git fetch origin +refs/pull/$PULP_FILE_PR_NUMBER/merge
  git checkout FETCH_HEAD
  pip install -e .
  cd ../pulp
fi

if [ -z $PULP_SMASH_PR_NUMBER ]; then
  pip install git+https://github.com/PulpQE/pulp-smash.git#egg=pulp-smash
else
  cd ../
  git clone https://github.com/PulpQE/pulp-smash.git
  cd pulp-smash
  git fetch origin +refs/pull/$PULP_SMASH_PR_NUMBER/merge
  git checkout FETCH_HEAD
  pip install -e .
  cd ../pulp
fi
