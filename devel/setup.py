from setuptools import setup, find_packages

setup(
    name='pulp-devel',
    version='2.7.0b6',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    )
