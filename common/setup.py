from setuptools import setup, find_packages

setup(
    name='pulp-common',
    version='2.15.2b2',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=['iniparse', 'isodate>=0.5.0']
)
