from setuptools import setup, find_packages

setup(
    name='pulp_node_consumer_extensions',
    version='2.17.1b3',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points={
        'pulp.extensions.consumer': [
            'repo_admin = pulp_node.extensions.consumer.commands:initialize',
        ]
    }
)
