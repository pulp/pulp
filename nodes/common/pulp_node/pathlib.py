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
import hashlib
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
    path = os.path.join(*[p.lstrip('/') for p in paths])
    return '/'.join((base.rstrip('/'), path))


def quote(path):
    return urllib.quote(path)


def checksum(path, bufsize=65535):
    _hash = hashlib.sha256()
    with open(path) as fp:
        while True:
            buf = fp.read(bufsize)
            if buf:
                _hash.update(buf)
            else:
                break
    return _hash.hexdigest()


def dir_checksum(path):
    tree = []
    parent_dir = os.path.dirname(path)
    for _dir, _dirs, _files in os.walk(path):
        tree.append(_dir.lstrip(parent_dir))
        file_paths = [os.path.join(_dir, f) for f in _files]
        tree.extend([(p.lstrip(parent_dir), checksum(p)) for p in file_paths])
    tree.sort()
    _hash = hashlib.sha256()
    _hash.update(str(tree))
    return _hash.hexdigest()