#!/usr/bin/env sh
set -ev

# add secret key to django settings.py
echo "SECRET_KEY = '$(cat /dev/urandom | tr -dc 'a-z0-9!@#$%^&*(\-_=+)' | head -c 50)'" >> pulpcore/pulpcore/app/settings.py

if [ "$DB" = 'postgres' ]; then
  sed -i "s/'ENGINE': 'django.db.backends.sqlite3'/'ENGINE': 'django.db.backends.postgresql_psycopg2'/" pulpcore/pulpcore/app/settings.py
  sed -i "s/'USER': ''/'USER': 'pulp'/" pulpcore/pulpcore/app/settings.py
  sed -i "s/\/var\/lib\/pulp\/sqlite3.db/pulp/" pulpcore/pulpcore/app/settings.py
  psql -U postgres -c 'CREATE USER pulp WITH SUPERUSER LOGIN;'
  psql -U postgres -c 'CREATE DATABASE pulp OWNER pulp;'
fi

mkdir -p ~/.config/pulp_smash
cp .travis/pulp-smash-config.json ~/.config/pulp_smash/settings.json

sudo mkdir /var/lib/pulp
sudo mkdir /var/cache/pulp
sudo chown travis:travis /var/lib/pulp
sudo chown travis:travis /var/cache/pulp
