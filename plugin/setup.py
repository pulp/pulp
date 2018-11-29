from setuptools import setup, find_packages

requirements = [
    'pulpcore>=3.0.0b16',
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
    version='0.1.0b14',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    url='http://www.pulpproject.org',
    python_requires='>=3.6',
    install_requires=requirements,
    include_package_data=True,
    classifiers=(
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    )
)
