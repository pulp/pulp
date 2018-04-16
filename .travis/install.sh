#!/usr/bin/env sh
set -v

install_pr () {
  SHA=$(curl https://api.github.com/repos/$1/pulls/$2 | jq -r '.merge_commit_sha')
  pushd ..
  git clone https://github.com/$1.git
  cd $(echo $1 | cut -d"/" -f2)
  git fetch origin +refs/pull/$2/merge
  git checkout $SHA
  pip install -e .
  popd
}

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
  install_pr "pulp/pulp_file" $PULP_FILE_PR_NUMBER
fi

if [ -z $PULP_SMASH_PR_NUMBER ]; then
  pip install git+https://github.com/PulpQE/pulp-smash.git#egg=pulp-smash
else
  install_pr "PulpQE/pulp-smash" $PULP_SMASH_PR_NUMBER
fi
