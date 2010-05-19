#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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

from setuptools import setup, find_packages


setup(
    name='pulp',
    version='0.0.1',
    description='content mangement and delivery',
    author='Jason L Connor, Mike McCune',
    author_email='jconnor@redhat.com, mmcune@redhat.com',
    url='',
    license='GPLv2+',
    packages=find_packages(),
    entry_points={'console_scripts': ['juicer = juicer.daemon:run',]},
    scripts=[],
    include_package_data=False,
    data_files=[],
    classifiers=[
        'License :: OSI Approved :: GNU General Puclic License (GPL)',
        'Programming Language :: Python',
        'Operating System :: POSIX',
        'Topic :: Content Management and Delivery',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
        'Development Status :: 3 - Alpha',
    ],
    requires=[
        'grinder >= 0.0.20',
        'python-pymongo = 1.6',
    ]
)

