from setuptools import setup, find_packages


setup(
    name='pulp-repoauth',
    version='2.16a1',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
)
