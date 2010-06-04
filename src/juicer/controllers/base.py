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
import sys
import traceback

try:
    import json
except ImportError:
    import simplejson as json
    
import pymongo.json_util 
import web


class JSONController(object):
    """
    Base controller class with convenience methods for JSON serialization
    """
    
    def input(self):
        return json.loads(web.data())
    
    def output(self, data):
        web.header('Content-Type', 'application/json')
        return json.dumps(data, default=pymongo.json_util.default)


def error_wrapper(method):
    """
    Controller class method wrapper that catches internal errors and reports
    them as JSON serialized trace back strings
    """
    @functools.wraps(method)
    def report_error(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception:
            exc_info = sys.exc_info()
            tb_msg = ''.join(traceback.format_exception(*exc_info))
            web.header('Content-Type', 'application/json')
            web.ctx.status = '500 Internal Server Error'
            return json.dumps(tb_msg)
    return report_error