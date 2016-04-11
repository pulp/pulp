#!/usr/bin/env python2

from setuptools import setup, find_packages

setup(
    name='pulp-client-lib',
    version='2.8.3b1',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=['isodate>0.5.0', 'm2crypto', 'okaara>=1.0.32', 'setuptools']
)
