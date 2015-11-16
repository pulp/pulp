#!/usr/bin/bash -e

#  When using this script, you will need to fix your database accordingly. If moving backward, you
#  will need to drop the database, and you will always need to run the migrations.

# You need the .bashrc that the Vagrant or dev-setup.sh environment creates. You can get it from
# playpen/ansible/roles/dev/files/bashrc if you aren't using one of those envs.
. ~/.bashrc

# Switch back to pulp-2.6
pstop

pushd ~/devel
for r in {pulp_deb,pulp_docker,pulp_openstack,pulp_ostree,pulp_puppet,pulp_python,pulp_rpm,pulp}; do
    if [ -d $r ]; then
        pushd $r
        sudo ./pulp-dev.py --uninstall
        popd
    fi
done

for repo in pulp pulp_puppet pulp_rpm
do
    pushd /home/vagrant/devel/$repo
    git checkout 2.6-dev
    find ~/devel -name "*.py[c0]" -delete
    sudo ./pulp-dev.py --install
    popd
done

popd # ~/devel

sudo dnf install -y python-webpy

workon pulp
pip install paste
