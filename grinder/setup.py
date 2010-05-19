#!/usr/bin/env python
#
# Copyright (c) 2008-2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Grinder Setup Script
"""

from setuptools import setup, find_packages


setup(
    name="grinder",
    version='0.1',
    description='A tool for synching content from the Red Hat Network.',
    author='Mike McCune, John Matthews',
    author_email='mmccune@redhat.com',
    url='http://github.com/mccun934/grinder',
    license='GPLv2+',

    package_dir={
        'grinder': 'src/grinder',
    },
    packages = find_packages('src'),
    include_package_data = True,
    data_files = [("../etc/grinder", ["etc/grinder/grinder.yml"])],
    # non-python scripts go here
    scripts = [
        'bin/grinder',
    ],

    classifiers = [
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Programming Language :: Python'
    ],
#    test_suite = 'nose.collector',
)


# XXX: this will also print on non-install targets
print("grinder target is complete")
