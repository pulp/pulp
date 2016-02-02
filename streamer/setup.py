import platform
from setuptools import setup, find_packages


# In EL twisted is still has sub-packages.
dist = platform.dist()
if dist[0] == 'redhat' and int(float(dist[1])) <= 7:
    twisted = ['twisted-core', 'twisted-web']
else:
    twisted = ['twisted']

setup(
    name='pulp-streamer',
    version='2.8.0b5',
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
