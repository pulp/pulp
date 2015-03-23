from setuptools import setup, find_packages

setup(
    name='pulp-client-admin',
    version='2.6.0',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points={
        'console_scripts': [
            'pulp-admin = pulp.client.admin:main'
        ],
        'pulp.extensions.admin': [
            'repo_admin = pulp.client.admin.cli:initialize',
        ],
    }
)
