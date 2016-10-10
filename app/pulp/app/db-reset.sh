#!/bin/bash

pushd `dirname "$0"`

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
python manage.py makemigrations pulp --noinput
python manage.py migrate --noinput
popd
