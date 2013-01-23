# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import os
import urllib2


def file_name_from_url(url):
    filename = url.rsplit('/', 1)[-1]
    assert filename
    return filename


def file_path_and_handle(storage_dir, file_name):
    path = os.path.abspath(os.path.join(storage_dir, file_name))
    handle = open(path, 'w')
    return path, handle


def fetch(url, storage_dir):
    name = file_name_from_url(url)
    path, handle = file_path_and_handle(storage_dir, name)

    body = urllib2.urlopen(url).read()

    handle.write(body)
    handle.close()

    return name
