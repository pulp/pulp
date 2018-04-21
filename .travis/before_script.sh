#!/usr/bin/env sh
set -v

if [ "$DB" = 'postgres' ]; then
  psql -U postgres -c 'CREATE USER pulp WITH SUPERUSER LOGIN;'
  psql -U postgres -c 'CREATE DATABASE pulp OWNER pulp;'
fi

mkdir -p ~/.config/pulp_smash
cp .travis/pulp-smash-config.json ~/.config/pulp_smash/settings.json

mkdir $HOME/pulp
mkdir $HOME/pulp/tmp

if [ "$DB" = 'postgres' ]; then
  export PULP_SETTINGS=$TRAVIS_BUILD_DIR/.travis/server.postgres.yaml
else
  # docs job also requires server.yaml
  export PULP_SETTINGS=$TRAVIS_BUILD_DIR/.travis/server.sqlite.yaml
fi

echo "SECRET_KEY: \"$(cat /dev/urandom | tr -dc 'a-z0-9!@#$%^&*(\-_=+)' | head -c 50)\"" | tee -a $PULP_SETTINGS
