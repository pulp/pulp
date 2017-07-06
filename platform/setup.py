from setuptools import setup, find_packages

requirements = [
    'celery',
    'coreapi',
    'Django>=1.8,<1.9',
    'django-filter',
    'djangorestframework',
    'drf-nested-routers',
    'psycopg2',
    'PyYAML',
    'setuptools',
    'pulpcore-common'
]

setup(
    name='pulpcore',
    description='Pulp Django Application and Related Modules',
    version='3.0.0a1.dev0',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=requirements,
    url='http://www.pulpproject.org',
    classifiers=(
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ),
    entry_points={
        'console_scripts': [
            'pulp-manager=pulpcore.app.entry_points:pulp_manager_entry_point'
        ]
    },
)
