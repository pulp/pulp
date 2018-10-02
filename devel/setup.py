import sys

from setuptools import setup, find_packages

PYTHON_MAJOR_MINOR = '%s.%s' % (sys.version_info[0], sys.version_info[1])

if PYTHON_MAJOR_MINOR < '2.7':
    requires = {'install_requires': ['argparse']}
else:
    requires = {}

setup(
    name='pulp-devel',
    version='2.17.1',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    **requires)
