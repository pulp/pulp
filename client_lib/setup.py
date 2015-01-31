from setuptools import setup, find_packages

setup(
    name='pulp-client-lib',
    version='2.5.3',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
)
