from setuptools import setup, find_packages


setup(
    name='pulp-server',
    version='2.6.0',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points={
        'console_scripts': [
            '../libexec/pulp-manage-workers = pulp.server.async.manage_workers:main',
            'pulp-manage-db = pulp.server.db.manage:main',
        ]
    }
)
