#!/bin/bash

pushd `dirname "$0"`

# If an optional argument to a virtual environment is passed, activate it.
if [ $# -gt 0 ]
  then
    source $1/bin/activate
fi

if [ -d migrations ]
then
# weird indentation here because the heredoc EOF terminator can't be indented
cat <<EOF
Platform 'migrations' dir already exists (`pwd`/migrations)
If resetting the DB fails, migrations for pulp apps (including platform)
may need to be removed for the DB reset to succeed.
EOF
sleep 1

fi

python manage.py reset_db --noinput
# the pulp platform app depends on auth being migrated before its own tables
# can be created, since we're using pulp's 'User' model as our AUTH_USER_MODEL
# this should only be required until we "makemigrations" and check those migrations
# in for the platform app, at which point we can declare this dependency in the
# migration itself:
# https://docs.djangoproject.com/en/1.8/topics/migrations/#dependencies
python manage.py makemigrations pulp_file
python manage.py makemigrations pulp_app
python manage.py migrate --noinput auth
python manage.py migrate --noinput
python manage.py reset-admin-password --password admin

if [ $# -gt 0 ]
  then
    deactivate
fi
popd
