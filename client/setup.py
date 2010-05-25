from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='client',
      version=version,
      description="Client side admin tools for Pulp server",
      long_description="""\
This package includes pulp cli and client side administration tools to manage content specific tasks against pulp server""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Pradeep Kilambi',
      author_email='pkilambi@redhat.com',
      url='https://fedorahosted.org/pulp/',
      license='GPLv2',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
