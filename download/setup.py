from setuptools import setup, find_packages

setup(
    name='pulp-download',
    version='3.0a1',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
)
