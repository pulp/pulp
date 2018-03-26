#!/usr/bin/env sh
set -v

result=0

if [ $TEST = 'docs' ]; then
  pip3 install sphinx sphinxcontrib-swaggerdoc
  cd docs
  make html
  if [ $? -ne 0 ]; then
    result=1
  fi
else
  # flake8
  flake8 --config flake8.cfg || exit 1

  if [ $TEST = 'pulp_file' ]; then
    pulp-manager makemigrations pulp_file --noinput
  fi

  pulp-manager makemigrations pulp_app --noinput

  pulp-manager migrate auth --noinput
  pulp-manager migrate --noinput
  if [ $? -ne 0 ]; then
    result=1
  fi

  pulp-manager test pulpcore/pulpcore/app/tests
  if [ $? -ne 0 ]; then
    result=1
  fi

  coverage run test

  pulp-manager reset-admin-password --password admin
  pulp-manager runserver >>~/django_runserver.log 2>&1 &
  celery worker -A pulpcore.tasking.celery_app:celery -n resource_manager@%h -Q resource_manager -c 1 --events --umask 18 >>~/resource_manager.log 2>&1 &
  celery worker -A pulpcore.tasking.celery_app:celery -n reserved_resource_worker_1@%h -c 1 --events --umask 18 >>~/reserved_workers-1.log 2>&1 &
  sleep 5

  if [ $TEST = 'pulp_file' ]; then
    py.test -v --color=yes --pyargs pulp_smash.tests.pulp3
  else
    py.test -v --color=yes --pyargs pulp_smash.tests.pulp3.pulpcore
  fi
  if [ $? -ne 0 ]; then
    result=1
    cat ~/django_runserver.log
    cat ~/resource_manager.log
    cat ~/reserved_workers-1.log
  fi

  if [ $DB = 'postgres' ]; then
    # make sure we actually ran postgres
    if [ -f '/var/lib/pulp/sqlite3.db' ]; then
      echo "Error!!!! sqlite database exists."
      result=1
    fi
  fi
fi

exit $result
