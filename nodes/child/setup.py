from setuptools import setup, find_packages

setup(
    name='pulp_node_child',
    version='2.6.0',
    license='GPLv2+',
    packages=find_packages(),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points={
        'pulp.importers': [
            'importer = pulp_node.importers.http.importer:entry_point',
        ],
    }
)
