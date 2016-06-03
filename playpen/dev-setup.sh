#!/bin/bash -e
#
# Beware that this script references distribution-specific items such as yum.
#
# Script summary:
#
# 1. Ensure script is not running as root.
# 2. Fetch a GitHub username from the user. In most cases, the user should have a
#    GitHub account and they should supply the name of that account.
# 3. Permanently disable SELinux. The user may refuse to do this step, in which
#    case the script will abort.
# 4. Use yum to install several packages.
# 5. Enable epel yum repositories.
# 6. Make a ~/devel directory and clone several Git repositories into the current
#    directory. These repositories are cloned via SSH, and they are cloned from
#    the GitHub user named at the beginning of this script. This means that
#    whoever is running this script should have a GitHub account with SSH keys,
#    and they should have already forked the repositories into their own account.
# 7. If no ansible inventory (a list of systems) exists at
#    `/tmp/ansible_inventory`, then create an inventory pointing to localhost.
# 8. Run `ansible-playbook`. Use the inventory file at `/tmp/ansible_inventory`
#    and the playbook at `ansible/dev-playbook.yml`.
# 9. Run the final configuration script, `vagrant-setup.sh`.

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

read -p 'Which plugin repos would you like to clone from your GitHub account? [crane pulp_deb pulp_docker pulp_openstack pulp_ostree pulp_puppet pulp_python pulp_rpm pulp-smash] ' REPOS
if [ "$REPOS" = "" ]; then
    REPOS="crane packaging pulp_deb pulp_docker pulp_openstack pulp_ostree pulp_puppet pulp_python pulp_rpm pulp-smash"
fi
# pulp is required and must be installed first so let's prepend it.
REPOS="pulp $REPOS"
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

echo "Install some prereqs"
sudo yum install -y ansible git redhat-lsb-core yum-utils

# repo setup
if ! rpm -q epel-release; then
    if [ "$(lsb_release -si)" = "CentOS" ]; then
        echo "setting up EPEL"
        sudo yum install -y epel-release
    elif [ "$(lsb_release -si)" = "RedHatEnterpriseServer" ]; then
        echo "setting up EPEL"
        sudo rpm -Uvh http://download.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
    fi
fi

mkdir -p $HOME/devel
pushd $HOME/devel
for r in $REPOS; do
  if [ ! -d $r ]; then
      echo "checking out $r code"
      git clone git@github.com:$GITHUB_USERNAME/$r
      echo "configuring remotes for $r"
      pushd $r
      # Configure the upstream remote
      if [ "$r" = "pulp-smash" ]; then
          git remote add -f upstream git@github.com:PulpQE/$r.git
      else
          git remote add -f upstream git@github.com:pulp/$r.git
      fi
      # Add the ability to checkout pull requests (git checkout pr/99 will check out #99!)
      git config --add remote.upstream.fetch '+refs/pull/*/head:refs/remotes/upstream/pr/*'
      # Set master's remote to upstream
      git config branch.master.remote upstream
      # Get the latest code from upstream
      git pull
      popd
  fi
done

# Install some of Ansible's dependencies
$HOME/devel/pulp/playpen/bootstrap-ansible.sh

pushd pulp
if [ ! -f /tmp/ansible_inventory ]; then
    echo -e "localhost ansible_connection=local" >> /tmp/ansible_inventory
fi
ansible-playbook --inventory-file=/tmp/ansible_inventory playpen/ansible/dev-playbook.yml
cd $HOME
bash -e $HOME/devel/pulp/playpen/vagrant-setup.sh
