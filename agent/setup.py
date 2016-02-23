#!/usr/bin/env python2

from setuptools import setup, find_packages

setup(
    name='pulp-agent',
    version='2.8.0b6',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=['m2crypto']
)
