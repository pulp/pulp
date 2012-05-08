# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""
Contains TASK event handler classes.
"""

import os
from pulp.server.event.dispatcher import *
from pulp.server.event.producer import EventProducer
from logging import getLogger

log = getLogger(__name__)


class ErrataEvent(EventHandler):
    """
    The I{errata} event handler.
    """
    
    ERRATA_FIELDS = (
        'id',
        'title',
        'description',
        'version',
        'release',
        'type',
        'status',
        'updated',
        'issued',
        'pushcount',
        'reboot_suggested',
        'references',
        'pkglist',
        'severity',
        'rights',
        'summary',
        'solution')

    def __init__(self):
        self.producer = EventProducer()

    @outbound(action='created')
    def create(self, *args, **kwargs):
        """
        Raise events when errata is created.
        @param errata: The created errata object.
        @type errata: Errata
        """
        errata = args[1]
        event = {}
        for k in self.ERRATA_FIELDS:
            event[k] = errata[k]
        self.producer.send('errata.created', event)
        
    @outbound(action='updated')
    def update(self, *args, **kwargs):
        """
        Raise events when errata is updated.
        @param errata: The updated errata object.
        @type errata: Errata
        """
        errata = args[1]
        event = {}
        for k in self.ERRATA_FIELDS:
            event[k] = errata[k]
        self.producer.send('errata.updated', event)


EventDispatcher.register('errata', ErrataEvent)
