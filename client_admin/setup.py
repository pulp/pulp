#!/usr/bin/env python3

from setuptools import setup, find_packages

requirements = [
    'pulpcore-common'
]

setup(
    name='pulpcore-cli',
    version='3.0.0a1.dev0',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=requirements,
    url='http://www.pulpproject.org',
    description='pulp-cli',
    entry_points={
        'console_scripts': [
            'pulp-admin = pulp.client.admin:main'
        ],
        'pulp.extensions.admin': [
            'repo_admin = pulp.client.admin.cli:initialize',
        ],
    }
)
