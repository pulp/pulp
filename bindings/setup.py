from setuptools import setup, find_packages

setup(
    name='pulp-bindings',
    version='2.6.0',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
)
