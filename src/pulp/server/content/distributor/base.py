# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


class Distributor(object):

    def __init__(self, **options):
        self.__dict__.update(options)

    @classmethod
    @property
    def types(cls):
        return []

    def publish(self, distributor_config, publish_config, publish_hook):
        raise NotImplementedError()

    def unpublish(self, distributor_config, unpublish_config, unpublish_hook):
        raise NotImplementedError()
