from setuptools import setup, find_packages

setup(
    name='pulp-streamer',
    version='2.8.0b2',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=[
        'iniparse',
        'mongoengine >= 0.7.10',
        'nectar >= 1.4.0',
        'setuptools',
        'twisted',
    ]
)
