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
sudo mkdir /var/cache/pulp
sudo mkdir /etc/pulp/
sudo chown -R travis:travis /var/lib/pulp
sudo chown travis:travis /var/cache/pulp

if [ "$DB" = 'postgres' ]; then
  sudo cp .travis/server.postgres.yaml /etc/pulp/server.yaml
else
  # docs job also requires server.yaml
  sudo cp .travis/server.sqlite.yaml /etc/pulp/server.yaml
fi

echo "SECRET_KEY: \"$(cat /dev/urandom | tr -dc 'a-z0-9!@#$%^&*(\-_=+)' | head -c 50)\"" | sudo tee -a /etc/pulp/server.yaml
