#!/bin/bash -x

# This assumes you're running in vagrant.
echo "drop database pulp; create database pulp owner pulp" | sudo -u postgres psql

rm -rf migrations

python manage.py makemigrations pulp --noinput
python manage.py migrate --noinput
