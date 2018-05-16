#!/usr/bin/env sh
set -v

result=0

if [ $TEST = 'docs' ]; then
  pip3 install sphinx sphinxcontrib-openapi
  cd docs
  make html
  if [ $? -ne 0 ]; then
    result=1
  fi
else
  # flake8
  flake8 --config flake8.cfg || exit 1

  pulp-manager makemigrations pulp_file --noinput

  pulp-manager makemigrations pulp_app --noinput

  pulp-manager migrate auth --noinput
  pulp-manager migrate --noinput
  if [ $? -ne 0 ]; then
    result=1
  fi

  coverage run manage.py test pulpcore
  if [ $? -ne 0 ]; then
    result=1
  fi

  export DJANGO_SETTINGS_MODULE=pulpcore.app.settings
  pulp-manager reset-admin-password --password admin
  coverage run $(which pulp-manager) runserver >> ~/django_runserver.log 2>&1 &
  coverage run $(which rq) worker -n 'resource_manager@%h' -w 'pulpcore.tasking.worker.PulpWorker' >> ~/resource_manager.log 2>&1 &
  coverage run $(which rq) worker -n 'reserved_resource_worker_1@%h' -w 'pulpcore.tasking.worker.PulpWorker' >> ~/reserved_worker-1.log 2>&1 &

  sleep 5

  py.test -v --color=yes --pyargs pulp_smash.tests.pulp3

  if [ $? -ne 0 ]; then
    result=1
    cat ~/django_runserver.log
    cat ~/resource_manager.log
    cat ~/reserved_worker-1.log
  fi

  ls -la
  bash <(curl -s https://codecov.io/bash) -c -F unittests
  rm -f .coverage

  pkill -f pulpcore.tasking.worker.PulpWorker
  sleep 5
  ls -la
  coverage combine
  ls -la
  bash <(curl -s https://codecov.io/bash) -c -F workers
  rm -f .coverage.travis*
  rm -f .coverage

  pkill -SIGINT -f runserver
  sleep 5
  ls -la
  bash <(curl -s https://codecov.io/bash) -c -F webserver

fi

exit $result
