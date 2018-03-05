#!/usr/bin/env sh
set -v

# dev_requirements should not be needed for testing; don't install them to make sure
pip install -r test_requirements.txt
pushd common/ && pip install -e . && popd
pushd pulpcore/ && pip install -e . && popd
pushd plugin/ && pip install -e .  && popd
pip install pytest git+https://github.com/PulpQE/pulp-smash.git#egg=pulp-smash

if [ $TEST = 'pulp_file' ]; then
  pip install git+https://github.com/pulp/pulp_file.git#egg=pulp_file
fi
