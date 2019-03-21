import platform
from setuptools import setup, find_packages


# In EL twisted is still has sub-packages.
dist = platform.dist()
if dist[0] in ('redhat', 'centos') and int(dist[1].split('.', 1)[0]) <= 7:
    twisted = ['twisted-core', 'twisted-web']
else:
    twisted = ['twisted']

setup(
    name='pulp-streamer',
    version='2.20a1',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=[
        'iniparse',
        'mongoengine >= 0.7.10',
        'nectar >= 1.4.0',
        'setuptools',
    ] + twisted,
    entry_points={
        'console_scripts': [
            'pulp_streamer = twisted.scripts.twistd:run'
        ]
    }
)
