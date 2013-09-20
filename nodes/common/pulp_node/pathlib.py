# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains convenience functions for dealing with both filesystem and URL
related paths.  Basically wrappers around os.path and urllib that compensates
for undesirable behaviors or modifies the behavior in ways that reduce code
duplication with in the nodes project.
"""

import os
import urllib
import errno


def mkdir(path):
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise e


def join(base, *paths):
    path = os.path.join(*[p.lstrip('/') for p in paths])
    return os.path.join(base.rstrip('/'), path)


def url_join(base, *paths):
    base = base.split('://', 1)
    base = '://'.join((base[0], base[1].rstrip('/')))
    path = os.path.join(*[p.lstrip('/') for p in paths])
    return '/'.join((base, path))


def quote(path):
    return urllib.quote(path)
