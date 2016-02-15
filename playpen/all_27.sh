#!/bin/bash
# Downgrade a Pulp system from master to 2.7.
#
# WARNING: This script enabled and disables system-wide yum/dnf repositories and
# performs other system-wide actions. Execute with care.
set -euo pipefail

# This associative array is incomplete. Patches welcome.
declare -rA repos_branches=(
    [pulp]=2.7-dev
    [pulp_docker]=1.0-dev
    [pulp_ostree]=1.0-dev
    [pulp_puppet]=2.7-dev
    [pulp_python]=1.0-dev
    [pulp_rpm]=2.7-dev
)

# Reinstall plugins we know how to handle, and uninstall all others.
pushd ~/devel
for repo in pulp pulp_*; do
    # Defend against e.g. a file named "pulp_log.txt".
    if [ ! -d "$repo" ]; then
        continue
    fi

    pushd "$repo"
    if [ -n "${repos_branches[$repo]:-}" ]; then
        git checkout "${repos_branches[$repo]}"
        find . -name '*.py[c0]' -delete
        sudo ./pulp-dev.py --install
    else
        sudo ./pulp-dev.py --uninstall
    fi
    popd
done
popd

set -x

# These aren't used by Pulp 2.7.
sudo rm /etc/httpd/conf.d/pulp_content.conf
sudo rm /etc/httpd/conf.d/pulp_streamer.conf

# Pulp 2.7 is incompatible with python-mongoengine >= 3 and python-pymongo >=
# 0.10.
sudo dnf  -y remove python-{mongoengine,pymongo}
sudo dnf config-manager --set-disabled pulp-nightlies
sudo dnf config-manager --set-enabled pulp-2.7-beta
sudo dnf -y install python-mongoengine-0.8.8 python-pymongo-2.5.2

fmt <<EOF
This script does not touch the Pulp database or change the state of Pulp
services. If downgrading from Pulp master, you may wish to execute the
following:
EOF
cat <<EOF

    mongo pulp_database --eval 'db.dropDatabase()'
    sudo -u apache pulp-manage-db
    prestart

EOF
fmt <<EOF
If upgrading from Pulp 2.6, you may wish to do something similar.
EOF
