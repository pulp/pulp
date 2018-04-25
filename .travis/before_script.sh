#!/usr/bin/env sh
set -v

if [ "$DB" = 'postgres' ]; then
  psql -U postgres -c 'CREATE USER pulp WITH SUPERUSER LOGIN;'
  psql -U postgres -c 'CREATE DATABASE pulp OWNER pulp;'
fi

mkdir -p ~/.config/pulp_smash
cp .travis/pulp-smash-config.json ~/.config/pulp_smash/settings.json

sudo mkdir /var/lib/pulp
sudo mkdir /var/lib/pulp/tmp
sudo mkdir /etc/pulp/
sudo chown -R travis:travis /var/lib/pulp

sudo cp .travis/server.yaml /etc/pulp/server.yaml

echo "SECRET_KEY: \"$(cat /dev/urandom | tr -dc 'a-z0-9!@#$%^&*(\-_=+)' | head -c 50)\"" | sudo tee -a /etc/pulp/server.yaml
