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

import hashlib
from pulp.server.dispatch import factory


class Capability:
    """
    An agent capability.
    @ivar context: The context.
    @type context: L{Context}
    """

    def __init__(self, context):
        """
        @param context: The capability context.
        @type context: L{Context}
        """
        self.context = context


class Context(object):

    def __init__(self, consumer):
        self.uuid = consumer['id']
        certificate = consumer.get('certificate')
        hash = hashlib.sha256()
        hash.update(certificate.strip())
        self.secret = hash.hexdigest()
        self.callid = factory.context().call_request_id
