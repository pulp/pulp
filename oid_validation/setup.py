#!/usr/bin/env python2

from setuptools import setup, find_packages


setup(
    name='pulp-oid_validation',
    version='2.8.1c2',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points={
        'pulp_content_authenticators': [
            'oid_validation=pulp.oid_validation.oid_validation:authenticate'
        ]
    },
)
