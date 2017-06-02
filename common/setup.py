from setuptools import setup, find_packages

setup(
    name='pulpcore-common',
    version='3.0a0.dev0',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    url='http://www.pulpproject.org',
    description='Common code for Pulp packages',
)
