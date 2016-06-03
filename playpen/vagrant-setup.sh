#!/usr/bin/bash

# Important things:
# - this file is still in-use, but deprecated in favor of ansible
# - the contents of this file are being converted to ansible tasks
# - add to the ansible playbook instead of adding to or altering this file
# - dev-setup script calls this script after running ansible, so (despite the
#   unfortunate name), it is *not* vagrant-specific

. ~/.bashrc

pushd devel
for r in {pulp,pulp_deb,pulp_docker,pulp_openstack,pulp_ostree,pulp_puppet,pulp_python,pulp_rpm}; do
  if [ -d $r ]; then
    echo "installing $r dev code"
    pushd $r
    # This command has an exit code of 1 when it works?
    ! mkvirtualenv --system-site-packages $r
    workon $r
    setvirtualenvproject
    # Install dependencies for automated tests
    pip install -r test_requirements.txt
    sudo python ./pulp-dev.py -I
    deactivate
    popd
  fi
done
# If crane is present, let's set it and its dependencies up as well
if [ -d crane ]; then
    echo "installing crane's environment"
    pushd crane
    ! mkvirtualenv --system-site-packages crane
    workon crane
    setvirtualenvproject
    # Install dependencies
    pip install -r test-requirements.txt

    cat << EOF > $HOME/devel/crane/crane.conf
[general]
data_dir: $HOME/devel/crane/metadata
debug: true
endpoint: $(hostname):5001
EOF

    deactivate
    popd
fi
# If pulp-smash is present, set it up
if [ -d pulp-smash ]; then
    echo "installing pulp-smash and its dependencies"
    pushd pulp-smash
    ! mkvirtualenv pulp-smash --python=python3
    workon pulp-smash
    setvirtualenvproject
    # Install dependencies
    pip install -r requirements.txt -r requirements-dev.txt
    pip install pytest
    python3 setup.py develop
    mkdir -p $HOME/.config/pulp_smash/
    cat << EOF > $HOME/.config/pulp_smash/settings.json
{
    "pulp": {
        "base_url": "https://$(hostname)",
        "auth": ["admin", "admin"],
        "cli_transport": "local",
        "verify": false
    }
}
EOF
    deactivate
    popd
fi
popd


# If there is no .vimrc, give them a basic one
if [ ! -f $HOME/.vimrc ]; then
    echo -e "set expandtab\nset tabstop=4\nset shiftwidth=4\n" > $HOME/.vimrc
fi

echo "Adjusting facls for apache"
setfacl -m user:apache:rwx $HOME

# Enable and start the Pulp services
echo "Starting more services"
for s in goferd httpd pulp_workers pulp_celerybeat pulp_resource_manager; do
  sudo systemctl enable $s
done


sudo -u apache pulp-manage-db;
setup_crane_links;
pstart;
ppopulate;

# Give the user some use instructions
if [ $USER = "vagrant" ]; then
    echo -e '\n\nDone. You can ssh into your development environment with vagrant ssh.\n'
fi
