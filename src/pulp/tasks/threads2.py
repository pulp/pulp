#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

__author__ = 'Jason L Connor <jconnor@redhat.com>'

import functools
import threading


Lock = threading.Lock

Condition = threading.Condition


class TaskThread(threading.Thread):
    """
    """
    def __init__(self, target, args=[], kwargs={}):
        super(TaskThread, self).__init__(target=target, args=args, kwargs=kwargs)
        self.__call = functools.partial(target, *args, **kwargs)
        self.__lock = threading.Lock()
        self.__exit = False
    
    def __yield(self):
        self.__lock.acquire()
        self.__lock.acquire()
    
    def __continue(self):
        if not self.__lock.locked():
            return
        self.__lock.release()
    
    def run(self):
        while True:
            self.__yield()
            if self.__exit:
                return
            self.__call()
    
    def execute(self):
        self.__continue()
    
    def exit(self):
        self.__exit = True
        self.__continue()