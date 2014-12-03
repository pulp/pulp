from setuptools import setup, find_packages

setup(
    name='pulp_node_admin_extensions',
    version='2.6.0',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points={
        'pulp.extensions.admin': [
            'repo_admin = pulp_node.extensions.admin.commands:initialize',
        ]
    }
)
