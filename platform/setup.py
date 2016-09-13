from setuptools import setup, find_packages

requirements = [
    'celery',
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
    classifiers=(
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ),
)
