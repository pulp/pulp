# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


def encode_unicode(path):
    """
    Check if given path is a unicode and if yes, return utf-8 encoded path
    """
    if type(path) is unicode:
        path = path.encode('utf-8')
    return path

def decode_unicode(path):
    """
    Check if given path is of type str and if yes, convert it to unicode
    """
    if type(path) is str:
        path = path.decode('utf-8')
    return path
