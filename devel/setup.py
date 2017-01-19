import sys

from setuptools import setup, find_packages

PYTHON_MAJOR_MINOR = '%s.%s' % (sys.version_info[0], sys.version_info[1])

requires = {'install_requires': ['mock<1.1']}

if PYTHON_MAJOR_MINOR < '2.7':
    requires['install_requires'].append('argparse')


setup(
    name='pulp-devel',
    version='2.13a1',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    **requires)
