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

import threading


CREATED = 'created'
PROCESSING = 'processing'
FINISHED = 'finished'
ERROR = 'error'


class Task(object):
    """
    """
    def __init__(self, callable, args, kwargs, callback_name=None):
        self.status = CREATED
        self.callable = callable
        self.args = args
        self.args = kwargs
        self.progress = None
        
        if callback_name is not None:
            self.kwargs[callback_name] = self.callback
            
        self.__thread = threading.Thread(target=self.callable,
                                         args=self.args,
                                         kwargs=self.kwargs)
        self.__thread.start()
        
    @property
    def ident(self):
        return self.__thread.ident
        
    def callback(self, current, total):
        if current == total:
            self.status = FINISHED
        self.progress = current / total
        
    def run(self):
        self.__thread.run()
        self.status = PROCESSING
        
    def check(self):
        if not self.__thread.is_alive():
            self.status = FINISHED
        return self.status