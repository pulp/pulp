from setuptools import setup, find_packages

requirements = [
    'pulpcore',
    'aiohttp',
    'aiofiles',
    'backoff',
]

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='pulpcore-plugin',
    description='Pulp Plugin API',
    long_description=long_description,
    version='0.0.1a1',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    url='http://www.pulpproject.org',
    install_requires=requirements,
    include_package_data=True,
    classifiers=(
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Django',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    )
)
