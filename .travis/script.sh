#!/usr/bin/env bash
# coding=utf-8

set -veuo pipefail

if [ "$TEST" = 'docs' ]; then
  cd docs
  make html
  set +euo pipefail
  return "$?"
fi



# Lint code.
flake8 --config flake8.cfg || exit 1

# Run unit tests.
coverage run manage.py test ./pulpcore/tests/unit/

# Run functional tests, and upload coverage report to codecov.
show_logs_and_return_non_zero() {
    readonly local rc="$?"
    cat ~/django_runserver.log
    cat ~/resource_manager.log
    cat ~/reserved_worker-1.log
    return "${rc}"
}
pytest -v -r sx --color=yes --pyargs tests.functional || show_logs_and_return_non_zero
pytest -v -r sx --color=yes --pyargs pulp_file.tests.functional || show_logs_and_return_non_zero
codecov

# Travis' scripts use unbound variables. This is problematic, because the
# changes made to this script's environment appear to persist when Travis'
# scripts execute. Perhaps this script is sourced by Travis? Regardless of why,
# we need to reset the environment when this script finishes.
#
# We can't use `trap cleanup_function EXIT` or similar, because this script is
# apparently sourced, and such a trap won't execute until the (buggy!) calling
# script finishes.
set +euo pipefail
