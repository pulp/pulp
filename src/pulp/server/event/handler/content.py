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
Contains REPO event handler classes.
"""

import os
from pulp.server.event.dispatcher import *
from pulp.server.event.producer import EventProducer
from logging import getLogger

log = getLogger(__name__)


class PackageEvent(EventHandler):
    """
    The I{package} event handler.
    """

    def __init__(self):
        self.producer = EventProducer()

    @outbound(action='created')
    def create(self, *args, **kwargs):
        """
        Raise events when a package is created.
        """
        pass

    @outbound(action='uploaded')
    def upload(self, *args, **kwargs):
        """
        Raise events when a package is uploaded.
        """
        event = dict(
            id=args[1], path=args[2])
        self.producer.send('package.uploaded', event)


    @outbound(action='deleted')
    def delete(self, *args, **kwargs):
        """
        Raise events when a package is deleted.
        """
        event = dict(
            id=args[1], path=args[2])
        self.producer.send('package.deleted', event)


class FileEvent(EventHandler):
    """
    The I{file} event handler.
    """

    def __init__(self):
        self.producer = EventProducer()

    @outbound(action='created')
    def create(self, *args, **kwargs):
        """
        Raise events when a file is created.
        """
        pass

    @outbound(action='uploaded')
    def upload(self, *args, **kwargs):
        """
        Raise events when a file is uploaded.
        """
        event = dict(
            id=args[1], path=args[2])
        self.producer.send('file.uploaded', event)


    @outbound(action='deleted')
    def delete(self, *args, **kwargs):
        """
        Raise events when a file is deleted.
        """
        event = dict(
            id=args[1], path=args[2])
        self.producer.send('file.deleted', event)


EventDispatcher.register('file', FileEvent)
EventDispatcher.register('package', PackageEvent)
