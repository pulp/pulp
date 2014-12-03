from setuptools import setup, find_packages

setup(
    name='pulp-client-consumer',
    version='2.6.0',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points={
        'console_scripts': [
            'pulp-consumer = pulp.client.consumer:main'
        ],
        'pulp.extensions.consumer': [
            'repo_admin = pulp.client.consumer.cli:initialize',
        ],
    }
)
