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


class DownloaderConfig(object):

    def __init__(self, **kwargs):

        # XXX solve the open-ended nature of the options with documentation?

        # TODO *ALL LOT* more validation than this

        protocol = kwargs.pop('protocol', None)
        if protocol is None:
            raise AttributeError('no protocol provided')

        self.protocol = protocol.lower()

        max_concurrent = kwargs.pop('max_concurrent', None)
        assert max_concurrent > 0 or max_concurrent is None

        self.max_concurrent = max_concurrent

        self.__dict__.update(kwargs)

    def __getattr__(self, item):
        return self.__dict__.get(item, None)

