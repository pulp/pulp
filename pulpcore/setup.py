from setuptools import setup, find_packages

with open('README.rst') as f:
    long_description = f.read()

requirements = [
    'coreapi',
    'Django>=1.11',
    'django-filter',
    'djangorestframework',
    'drf-nested-routers',
    'drf-yasg',
    'psycopg2-binary',
    'PyYAML',
    'rq',
    'setuptools',
    'pulpcore-common==3.0.0b2'
]

setup(
    name='pulpcore',
    description='Pulp Django Application and Related Modules',
    long_description=long_description,
    version='3.0.0b4',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=requirements,
    include_package_data=True,
    url='http://www.pulpproject.org',
    classifiers=(
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ),
    entry_points={
        'console_scripts': [
            'pulp-manager=pulpcore.app.entry_points:pulp_manager_entry_point'
        ]
    },
)
