#!/bin/bash -e

if [[ $EUID -eq 0 ]]; then
    echo "You are running this script as root."
    echo "This script needs to be run as a non-root user with sudo access."
    exit 1
fi

read -p "What is your GitHub username? [$USER] " GITHUB_USERNAME
if [ "$GITHUB_USERNAME" = "" ]; then
    GITHUB_USERNAME="$USER"
fi
echo "Choosing $GITHUB_USERNAME as your GitHub username."

read -p 'Where would you like your code checked out? [$HOME/devel] ' DEVEL_PATH
if [ "$DEVEL_PATH" = "" ]; then
    DEVEL_PATH="$HOME/devel"
fi
echo "Choosing $DEVEL_PATH as your development path."

read -p 'Which repos would you like to clone from your GitHub account? [pulp pulp_docker pulp_openstack pulp_ostree pulp_puppet pulp_python pulp_rpm] ' REPOS
if [ "$REPOS" = "" ]; then
    REPOS="pulp pulp_docker pulp_openstack pulp_ostree pulp_puppet pulp_python pulp_rpm"
fi
echo "These repos will be cloned into your development path: $REPOS"

if [ $# = 0 ]; then
    if [ $(getenforce) = "Enforcing" ]; then
        echo "Dev setup does not work with selinux enabled."
        echo "Selinux will be disabled immediately and for future restarts."
        while true; do
            read -p "Do you want to proceed? (y/n) " yn
            case $yn in
                    [Yy]) break;;
                    [Nn]) echo "Aborting."; exit 1;;
                    *) echo "Please, answer y or n.";;
            esac
        done
    fi
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

if [ $(getenforce) = "Enforcing" ]; then
    echo "Disabling selinux for dev install"
    # dev setup does not work with selinux at this time
    sudo setenforce 0
    sudo sed -i 's/enforcing/permissive/' /etc/sysconfig/selinux
fi

echo "Install some prereqs"
sudo yum install -y wget yum-utils redhat-lsb-core

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
        sudo rpm -Uvh http://download.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
    fi
fi
sudo yum-config-manager --enable pulp-2.6-beta > /dev/null
sudo yum-config-manager --enable pulp-2.6-testing > /dev/null
popd

echo "installing some dev tools"
sudo yum install -y vim-enhanced python-virtualenvwrapper

if ! grep WORKON_HOME ~/.bashrc; then
    echo "Setting up virtualenv"
    echo -e "# Set up virtualenvwrapper\nexport WORKON_HOME=$HOME/.virtualenvs\nexport PIP_VIRTUALENV_BASE=$WORKON_HOME\nexport VIRTUALENV_USE_DISTRIBUTE=true\nexport PIP_RESPECT_VIRTUALENV=true\nsource /usr/bin/virtualenvwrapper.sh" >> ~/.bashrc
fi
# We always need to source those variables from the bashrc, in case the user is running this for the
# first time, or invoking the script directly with bash.
. ~/.bashrc

# install rpms, then remove pulp*
echo "installing RPMs"
sudo yum install -y @pulp-server-qpid @pulp-admin @pulp-consumer
sudo yum remove -y pulp-\* python-pulp\*
sudo yum install -y git mongodb mongodb-server python-django python-flake8 python-mock \
                    python-mongoengine python-nose python-paste python-pip python-qpid-qmf \
                    python-setuptools python-sphinx qpid-cpp-server qpid-cpp-server-store


mkdir -p $DEVEL_PATH
pushd $DEVEL_PATH
for r in $REPOS; do
  if [ ! -d $r ]; then
      echo "checking out $r code"
      git clone git@github.com:$GITHUB_USERNAME/$r
      echo "installing $r dev code"
      pushd $r
      # Configure the upstream remote
      git remote add -f upstream git@github.com:pulp/$r.git
      # Add the ability to checkout pull requests (git checkout pr/99 will check out #99!)
      git config --add remote.upstream.fetch '+refs/pull/*/head:refs/remotes/origin/pr/*'
      # Set master's remote to upstream
      git config branch.master.remote upstream
      # Get the latest code from upstream
      git pull
      # This command has an exit code of 1 when it works?
      ! mkvirtualenv --system-site-packages $r
      workon $r
      setvirtualenvproject
      deactivate
      sudo python ./pulp-dev.py -I
      popd
  fi
done

# If there is no .vimrm, give them a basic one
if [ ! -f $HOME/.vimrc ]; then
    echo -e "set expandtab\nset tabstop=4\nset shiftwidth=4\n" > $HOME/.vimrc
fi

echo "Adjusting facls for apache"
setfacl -m user:apache:rwx $HOME


echo "Starting services, this may take a few minutes due to mongodb journal allocation"
for s in qpidd goferd mongod; do
  sudo systemctl enable $s
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

if [ ! -f $HOME/.pulp/user-cert.pem ]; then
    echo "Logging in"
    pulp-admin login -u admin -p admin
fi

if [ "$(pulp-admin rpm repo list | grep zoo)" = "" ]; then
    echo "Creating and syncing the example zoo repository"
    pulp-admin rpm repo create --repo-id zoo --feed \
        https://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/zoo/ --relative-url zoo
    pulp-admin rpm repo sync run --repo-id zoo
fi

echo -e '\n\nDone. You should be able to run 'pulp-admin' successfully! Here are some tips:\n'
echo -e "\t* If this is your first time running this script, you should source your .bashrc file:\n"
echo -e "\t\t$ . ~/.bashrc"
echo -e "\n\t* Your code is all checked out inside of $DEVEL_PATH."
echo -e "\n\t* The default username:password is admin:admin. When your session expires, you can log"
echo -e "\t  in again with pulp-admin login -u admin"
echo -e "\n\t* In each repository, you can checkout PRs with git checkout pr/<#>. For example:\n"
echo -e "\t\t$ git checkout pr/99"
echo -e "\n\t* Your GitHub account is the origin remote, and Pulp's is the upstream remote."
echo -e "\n\t* master's remote is configured to upstream. To push changes to your master branch:\n"
echo -e "\t\t$ git push origin master"
echo -e "\n\t* You can type workon <project> to quickly cd to a project dir and activate its "
echo -e "\t  virtualenv. For example:\n"
echo -e "\t\t$ workon pulp_python\n"
