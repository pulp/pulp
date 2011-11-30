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

import datetime
import threading

from pulp.common import dateutils
from pulp.server.dispatch import call
from pulp.server.util import Singleton


class Scheduler(object):

    __metaclass__ = Singleton

    def __init__(self, dispatch_interval=30):

        self.dispatch_interval = dispatch_interval

        self.__exit = False
        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)

        self.__dispatcher = threading.Thread(target=self.__dispatch)
        self.__dispatcher.setDaemon(True)
        self.__dispatcher.start()

    def __dispatch(self):
        self.__lock.acquire()
        while True:
            self.__condition.wait(timeout=self.dispatch_interval)
            if self.__exit:
                if self.__lock is not None:
                    self.__lock.release()
                return
            # TODO find scheduled tasks here
            now = datetime.datetime.now(dateutils.utc_tz())

    def exit(self):
        self.__exit = True

    # schedule control ---------------------------------------------------------

    def add(self, call_request, schedule):
        pass

    def remove(self, schedule_id):
        pass

    # query methods ------------------------------------------------------------

    def find(self, **criteria):
        pass

    def history(self, **criteria):
        pass
