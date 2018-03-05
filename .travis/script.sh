#!/usr/bin/env sh
set -ev

if [ $DB = 'docs' ]; then
  pip3 install sphinx sphinxcontrib-swaggerdoc
  cd docs
  make html
else
  # flake8
  flake8 --config flake8.cfg

  pulp-manager makemigrations pulp_app --noinput
  pulp-manager migrate auth --noinput
  pulp-manager migrate --noinput && pulp-manager test
  pulp-manager test pulpcore/pulpcore/app/tests
  pulp-manager reset-admin-password --password admin
  pulp-manager runserver >>~/django_runserver.log 2>&1 &
  celery worker -A pulpcore.tasking.celery_app:celery -n resource_manager@%h -Q resource_manager -c 1 --events --umask 18 >>~/resource_manager.log 2>&1 &
  celery worker -A pulpcore.tasking.celery_app:celery -n reserved_resource_worker_1@%h -c 1 --events --umask 18 >>~/reserved_workers-1.log 2>&1 &
  sleep 5
  py.test -v --color=yes --pyargs pulp_smash.tests.pulp3.pulpcore
  cat ~/django_runserver.log
  cat ~/resource_manager.log
  cat ~/reserved_workers-1.log
fi
