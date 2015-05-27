#!/bin/bash -e

if [ $(getenforce) = "Enforcing" ]; then
    echo "Disabling selinux for dev install"
    # dev setup does not work with selinux at this time
    sudo setenforce 0
    sudo sed -i 's/enforcing/permissive/' /etc/sysconfig/selinux
fi


if ! sudo grep -q "StrictModes no" /etc/ssh/sshd_config; then
    echo -e "\nIn some setups (eg. Vagrant), it is necessary to disable"
    echo "ssh strict modes to access the machine with key based authentication."
    echo "StrictModes will be disabled now and for future restarts."
    echo "Disabling StrictModes"
    sudo sed -i 's/#StrictModes yes/StrictModes no/' /etc/ssh/sshd_config
    sudo systemctl restart sshd
fi


echo "Install some prereqs"
sudo dnf install -y wget yum-utils redhat-lsb-core

echo "setting up repos"
# repo setup
pushd /etc/yum.repos.d
if [ "$(lsb_release -si)" = "Fedora" ]; then
    if [ ! -f fedora-pulp.repo ]; then
        sudo wget -q https://repos.fedorapeople.org/repos/pulp/pulp/fedora-pulp.repo
    fi
else
    if [ ! -f rhel-pulp.repo ]; then
        sudo wget -q https://repos.fedorapeople.org/repos/pulp/pulp/rhel-pulp.repo
    fi
    if ! rpm -q epel-release; then
        if [ "$(lsb_release -si)" = "CentOS" ]; then
            sudo dnf install -y epel-release
        else
            sudo rpm -Uvh http://download.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
        fi
    fi
fi
sudo yum-config-manager --enable pulp-2.6-beta > /dev/null
sudo yum-config-manager --enable pulp-2.6-testing > /dev/null
popd

echo "installing some dev tools"
sudo dnf install -y vim-enhanced python-virtualenvwrapper bash-completion \
                    python-django-bash-completion

if ! grep WORKON_HOME ~/.bashrc; then
    echo "Setting up virtualenv"
    echo -e "# Set up virtualenvwrapper\nexport WORKON_HOME=$HOME/.virtualenvs\nexport PIP_VIRTUALENV_BASE=$WORKON_HOME\nexport VIRTUALENV_USE_DISTRIBUTE=true\nexport PIP_RESPECT_VIRTUALENV=true\nsource /usr/bin/virtualenvwrapper.sh" >> ~/.bashrc
fi
if ! grep DJANGO_SETTINGS_MODULE ~/.bashrc; then
    echo "export DJANGO_SETTINGS_MODULE=pulp.server.webservices.settings" >> ~/.bashrc
fi
# We always need to source those variables from the bashrc, in case the user is running this for the
# first time, or invoking the script directly with bash.
. ~/.bashrc

# install rpms, then remove pulp*
echo "installing RPMs"
sudo dnf install -y @pulp-server-qpid @pulp-admin @pulp-consumer
sudo dnf remove --setopt=clean_requirements_on_remove=false -y pulp-\* python-pulp\*
sudo dnf install -y git mongodb mongodb-server python-debian python-django python-glanceclient \
                    python-keystoneclient python-mongoengine python-paste python-qpid-qmf \
                    python-setuptools python-sphinx qpid-cpp-server qpid-cpp-server-store

# disable mongo journaling since this is a dev setup
echo "Disabling MongoDB journal and starting services"
sudo sed -i 's/journal = true/nojournal = true/' /etc/mongodb.conf
for s in qpidd mongod; do
  sudo systemctl enable $s
  sudo systemctl start $s
done


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
    ./run-tests.py -x --enable-coverage
    deactivate
    popd
  fi
done

# If there is no .vimrm, give them a basic one
if [ ! -f /home/vagrant/.vimrc ]; then
    echo -e "set expandtab\nset tabstop=4\nset shiftwidth=4\n" > /home/vagrant/.vimrc
fi

echo "Adjusting facls for apache"
setfacl -m user:apache:rwx /home/vagrant

echo "populating mongodb"
sudo -u apache pulp-manage-db

echo "Starting more services"
for s in goferd httpd pulp_workers pulp_celerybeat pulp_resource_manager; do
  sudo systemctl enable $s
  sudo systemctl start $s
done

echo "Disabling SSL verification on dev setup"
sudo sed -i 's/# verify_ssl: True/verify_ssl: False/' /etc/pulp/admin/admin.conf

if [ ! -f /home/vagrant/.pulp/user-cert.pem ]; then
    echo "Logging in"
    pulp-admin login -u admin -p admin
fi

if [ "$(pulp-admin rpm repo list | grep zoo)" = "" ]; then
    echo "Creating and syncing the example zoo repository"
    pulp-admin rpm repo create --repo-id zoo --feed \
        https://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/zoo/ --relative-url zoo
    pulp-admin rpm repo sync run --repo-id zoo
fi

# Give the user some use instructions
sudo cp /home/vagrant/devel/pulp/playpen/vagrant-motd.txt /etc/motd
echo -e '\n\nDone. You can ssh into your development environment with vagrant ssh.\n'
