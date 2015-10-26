#!/usr/bin/bash

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
    sudo dnf install -y $(rpmspec -q --queryformat '[%{REQUIRENAME}\n]' *.spec | grep -v "/.*" | grep -v "python-pulp.* " | grep -v "pulp.*" | uniq)
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
    sudo dnf install -y $(rpmspec -q --queryformat '[%{REQUIRENAME}\n]' python-crane.spec | grep -v "/.*" | uniq)
    pip install -r test-requirements.txt

    cat << EOF > $HOME/devel/crane/crane.conf
[general]
data_dir: $HOME/devel/crane/metadata
debug: true
endpoint: pulp-devel:5001
EOF

    mkdir -p metadata/v1 metadata/v2
    sudo mkdir -p /var/lib/pulp/published/docker/v1 /var/lib/pulp/published/docker/v2
    sudo chown apache:apache /var/lib/pulp/published/docker/v1
    sudo chown apache:apache /var/lib/pulp/published/docker/v2
    sudo ln -s $HOME/devel/crane/metadata/v1 /var/lib/pulp/published/docker/v1/app
    sudo ln -s $HOME/devel/crane/metadata/v2 /var/lib/pulp/published/docker/v2/app

    deactivate
    popd
fi
# If pulp-smash is present, set it up
if [ -d pulp-smash ]; then
    echo "installing pulp-smash and its dependencies"
    pushd pulp-smash
    ! mkvirtualenv --system-site-packages pulp-smash
    workon pulp-smash
    setvirtualenvproject
    # Install dependencies
    pip install -r requirements.txt -r requirements-dev.txt
    python setup.py develop
    mkdir -p $HOME/.config/pulp_smash/
    cat << EOF > $HOME/.config/pulp_smash/settings.json
{
    "default": {
        "base_url": "https://dev.example.com",
        "auth": ["admin", "admin"],
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

echo "populating mongodb"
sudo -u apache pulp-manage-db

# Enable and start the Pulp services
echo "Starting more services"
for s in goferd httpd pulp_workers pulp_celerybeat pulp_resource_manager; do
  sudo systemctl enable $s
done
pstart

echo "Disabling SSL verification on dev setup"
sudo sed -i 's/# verify_ssl: True/verify_ssl: False/' /etc/pulp/admin/admin.conf

if [ ! -f $HOME/.pulp/user-cert.pem ]; then
    echo "Logging in"
    pulp-admin login -u admin -p admin
fi

if [ -d $HOME/devel/pulp_rpm ]; then
    if [ "$(pulp-admin rpm repo list | grep zoo)" = "" ]; then
        echo "Creating the example zoo repository"
        pulp-admin rpm repo create --repo-id zoo --feed \
            https://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/zoo/ --relative-url zoo
    fi
fi

# Give the user some use instructions
sudo cp $HOME/devel/pulp/playpen/vagrant-motd.txt /etc/motd
if [ $USER = "vagrant" ]; then
    echo -e '\n\nDone. You can ssh into your development environment with vagrant ssh.\n'
fi
