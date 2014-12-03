#!/bin/bash

if [[ $EUID -eq 0 ]]; then
    echo "You are running this script as root."
    echo "This script needs to be run as a non-root user with sudo access."
    exit 1
fi

if [ $# = 0 ]; then
    echo "Dev setup does not work with selinux enabled."
    echo "Selinux will be disabled immediately and for future restarts."
    while true; do
        read -p "Do you want to proceed?(y/n)" yn
        case $yn in
                [Yy]) break;;
                [Nn]) echo "Aborting."; exit 1;;
                *) echo "Please, answer y or n.";;
        esac
    done
else
    case "$1" in
        -h|--help)
            echo -e "Usage:\n$0 [options]\n"
            echo "Options:"
            echo "-h, --help                    show this help message and exit"
            echo "-d, --disable-selinux         disables selinux immediately and for future restarts for dev setup"
            exit 0
            ;;
        -d|--disable-selinux)
            :;;
        *)
            echo "Not a valid option. See --help"
            exit 1
            ;;
    esac
fi

echo "Disabling selinux for dev install"
# dev setup does not work with selinux at this time
sudo setenforce 0
sudo sed -i 's/enforcing/permissive/' /etc/sysconfig/selinux

echo "Install some prereqs"
sudo yum install -y wget yum-utils

echo "setting up repos"
# repo setup
pushd /etc/yum.repos.d
sudo wget -q https://repos.fedorapeople.org/repos/pulp/pulp/fedora-pulp.repo
sudo yum-config-manager --enable pulp-2.6-testing > /dev/null
popd

# install rpms, then remove pulp*

echo "installing RPMs"
sudo yum install -y @pulp-server-qpid @pulp-admin @pulp-consumer
sudo yum remove -y pulp-\* python-pulp\*
sudo yum install -y python-setuptools redhat-lsb mongodb mongodb-server \
                    qpid-cpp-server qpid-cpp-server-store python-qpid-qmf \
                    git python-pip python-nose python-mock python-paste
sudo yum-config-manager --disable pulp-2.6-testing > /dev/null

echo "installing newer kombu (temporary step until 2.6.0 is in testing repo)"
sudo rpm -Uvh http://koji.katello.org/packages/python-kombu/3.0.15/13.pulp.fc20/noarch/python-kombu-3.0.15-13.pulp.fc20.noarch.rpm

pushd ~
for r in pulp pulp_rpm; do
  echo "checking out $r code"
  git clone https://github.com/pulp/$r
  echo "installing $r dev code"
  pushd $r
  sudo python ./pulp-dev.py -I
  sudo ./manage_setup_pys.sh develop
  popd
done

echo "Adjusting facls for apache"
setfacl -m user:apache:rwx .
pushd pulp
setfacl -m user:apache:rwx .
popd; popd


echo "Starting services, this may take a few minutes due to mongodb journal allocation"
for s in qpidd goferd mongod; do
  sudo systemctl start $s
done

echo "populating mongodb"
sudo -u apache pulp-manage-db

echo "Starting more services"
for s in httpd pulp_workers pulp_celerybeat pulp_resource_manager; do
  sudo systemctl start $s
done

echo "Disabling SSL verification on dev setup"
sudo sed -i 's/# verify_ssl: True/verify_ssl: False/' /etc/pulp/admin/admin.conf
echo "done! you should be able to run 'pulp-admin login -u admin' now to log in"
echo "To run tests, cd to pulp or pulp_rpm and run \"./run-tests.py\""

