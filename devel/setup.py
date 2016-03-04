from setuptools import setup, find_packages


setup(
    name='pulp-devel',
    version='2.8.0b8',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com')
