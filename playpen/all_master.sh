#!/bin/bash

#  When using this script, you will need to fix your database accordingly. If moving backward, you
#  will need to drop the database, and you will always need to run the migrations.


for repo in pulp_docker pulp_puppet pulp_python pulp_rpm pulp
do
    pushd /home/vagrant/devel/$repo
    sudo ./pulp-dev.py --uninstall
    git checkout master
    find ~/devel -name "*.py[c0]" -delete
    popd
done

for repo in pulp pulp_docker pulp_puppet pulp_python pulp_rpm
do
    pushd /home/vagrant/devel/$repo
    sudo ./pulp-dev.py --install
    popd
done
