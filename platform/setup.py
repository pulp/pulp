from setuptools import setup, find_packages

requirements = [
    'Django>=1.8,<1.9',
    'django-extensions',
    'djangorestframework',
    'psycopg2',
    'PyYAML',
    'setuptools',
]

setup(
    name='pulp-platform',
    version='3.0a1',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=requirements,
)
