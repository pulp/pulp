#!/usr/bin/env sh

pip install twine

pushd $1
python setup.py sdist bdist_wheel --python-tag py3
twine upload dist/* -u pulp -p $PYPI_PASSWORD
exit $?
