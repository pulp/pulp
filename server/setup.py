import sys

from setuptools import setup, find_packages

PYTHON_MAJOR_MINOR = '%s.%s' % (sys.version_info[0], sys.version_info[1])

# Django 1.8.0 requires Python >= 2.7
if PYTHON_MAJOR_MINOR < '2.7':
    DJANGO_REQUIRES = 'django >=1.4.0, <1.8.0'
else:
    DJANGO_REQUIRES = 'django>=1.4.0'

# semantic_version and m2crypto no longer install via pip on el5,
# and need to be pinned to the highest known working version in py2.4
if PYTHON_MAJOR_MINOR > '2.4':
    SEMVER_REQUIRES = 'semantic_version>=2.2.0'
    M2CRYPTO_REQUIRES = 'm2crypto'
else:
    SEMVER_REQUIRES = 'semantic_version>=2.2.0,<2.5'
    M2CRYPTO_REQUIRES = 'm2crypto<0.24'

setup(
    name='pulp-server',
    version='2.17.1',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points={
        'console_scripts': [
            'pulp-manage-db = pulp.server.db.manage:main',
        ]
    },
    install_requires=[
        'blinker', 'celery >=3.1.0', 'httplib2', 'iniparse', 'isodate>=0.5.0',
        'mongoengine>=0.10.0', 'oauth2>=1.5.211', 'pymongo>=3.0.0', 'setuptools',
        DJANGO_REQUIRES, SEMVER_REQUIRES, M2CRYPTO_REQUIRES],
)
