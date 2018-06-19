#!/bin/bash
# install packages deps required to build docs
sudo apt-get install graphviz plantuml python-virtualenv postgresql-devel python3-devel gcc -y

git config --global user.email "pulp-infra@redhat.com"
git config --global user.name "pulpbot"
git config --global push.default simple
set -x

# Add github.com as a known host
echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" >> /home/jenkins/.ssh/known_hosts
echo "docs.pulpproject.org,8.43.85.236 ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBGXG+8vjSQvnAkq33i0XWgpSrbco3rRqNZr0SfVeiqFI7RN/VznwXMioDDhc+hQtgVhd6TYBOrV07IMcKj+FAzg=" >> /home/jenkins/.ssh/known_hosts

chmod 644 /home/jenkins/.ssh/known_hosts

# create a virtualenv in which to install packages needed to build docs
virtualenv -p /usr/bin/python3 --system-site-packages ~/docs_ve
source ~/docs_ve/bin/activate
pip3 install celery 'django<2' django-filter djangorestframework==3.6.4 djangorestframework-jwt drf-nested-routers psycopg2 sphinx git+https://github.com/snide/sphinx_rtd_theme.git@abfa98539a2bfc44198a9ca8c2f16efe84cc4d26 pyyaml virtualenv

# create server.yaml config file
sudo mkdir -p /etc/pulp
echo "SECRET_KEY: '$(cat /dev/urandom | tr -dc 'a-z0-9\!@#$%^&*(\-_=+)' | head -c 50)'" | sudo tee -a /etc/pulp/server.yaml

# clone and build the docs
cd pulp-ci/ci/
export PYTHONUNBUFFERED=1
python3 docs-builder.py --release 2-master
