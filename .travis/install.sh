#!/usr/bin/env sh
set -v

# dev_requirements should not be needed for testing; don't install them to make sure
pip install "Django<=$DJANGO_MAX"
pip install -r test_requirements.txt
pushd common/ && pip install -e . && popd
pushd pulpcore/ && pip install -e . && popd
pushd plugin/ && pip install -e .  && popd

if [ "$TEST" = 'docs' ]; then
  pip3 install 'sphinx<1.8.0' sphinxcontrib-openapi sphinx_rtd_theme
  return "$?"
fi

export COMMIT_MSG=$(git show HEAD^2 -s)
export PULP_FILE_PR_NUMBER=$(echo $COMMIT_MSG | grep -oP 'Required\ PR:\ https\:\/\/github\.com\/pulp\/pulp_file\/pull\/(\d+)' | awk -F'/' '{print $7}')

if [ -z "$PULP_FILE_PR_NUMBER" ]; then
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
