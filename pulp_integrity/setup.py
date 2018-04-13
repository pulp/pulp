from setuptools import setup, find_packages

setup(
    name='pulp_integrity',
    version='2.16',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description="A fsck-like tool to generate a Pulp integrity report.",
    entry_points={
        'console_scripts': [
            'pulp-integrity = pulp_integrity.integrity:main',
        ],
        'validators': [
            'checksum = pulp_integrity.generic:ChecksumValidator',
            'dark_content = pulp_integrity.generic:DarkContentValidator',
            'existence = pulp_integrity.generic:ExistenceValidator',
            'size = pulp_integrity.generic:SizeValidator',
        ],
    },
)
