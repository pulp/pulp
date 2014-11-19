from setuptools import setup, find_packages

setup(
    name='pulp_node_parent',
    version='2.6.0',
    license='GPLv2+',
    packages=find_packages(),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points={
        'pulp.distributors': [
            'distributor = pulp_node.distributors.http.distributor:entry_point',
        ],
        'pulp.profilers': [
            'profiler = pulp_node.profilers.nodes:entry_point'
        ]
    }
)
