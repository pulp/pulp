from setuptools import setup, find_packages

requirements = ['requests_futures']

setup(
    name='pulp-plugin',
    version='3.0a1',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=requirements,
)
