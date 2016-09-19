#!/bin/bash

cd `dirname "$0"`
if [ -d migrations ]
then
    echo "Platform 'migrations' dir already exists (`pwd`/migrations)"
    echo "If resetting the DB fails, migrations for pulp apps (including platform)"
    echo "may need to be removed for the DB reset to succeed."
    echo ""
    echo "Continuing in 3 seconds."
    sleep 3
fi
python manage.py reset_db --noinput
python manage.py makemigrations pulp --noinput
python manage.py migrate --noinput
