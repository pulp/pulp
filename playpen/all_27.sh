#!/bin/bash

#  When using this script, you will need to fix your database accordingly. If moving backward, you
#  will need to drop the database, and you will always need to run the migrations.


# pulp_docker, pulp_python, pulp_ostree excluded because they are versioned differently
for repo in pulp pulp_puppet pulp_rpm
do
    pushd /home/vagrant/devel/$repo
    git checkout 2.7-dev
    find ~/devel -name "*.py[c0]" -delete
    sudo ./pulp-dev.py --install
    popd
done

for repo in pulp_docker pulp_python
do
    pushd /home/vagrant/devel/$repo
    sudo ./pulp-dev.py --uninstall
    popd
done
