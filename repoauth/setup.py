from setuptools import setup, find_packages


setup(
    name='pulp-repoauth',
    version='2.15.2b2',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
)
