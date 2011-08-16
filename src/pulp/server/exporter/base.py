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
import os
import logging
import pulp.server.util as util
from pulp.server.db import connection
log = logging.getLogger(__name__)

class BaseExporter(object):
    """
     Base Exporter module with common methods
    """
    def __init__(self, repoid, target_dir="./", start_date=None, end_date=None, make_isos=False):
        """
        initialize exporter
        @param repoid: repository Id
        @type repoid: string
        @param target_dir: target directory where exported content is written
        @type target_dir: string
        @param start_date: optional start date from which the content needs to be exported
        @type start_date: date
        @param end_date: optional end date from which the content needs to be exported
        @type end_date: date
        @param make_isos: flag to indicate iso generation
        @type make_isos: boolean
        """
        self.repoid = repoid
        self.target_dir = target_dir
        self.start_date = start_date
        self.end_date = end_date
        self.make_isos = make_isos
        self.progress = {
            'status': 'running',
            'item_name': None,
            'item_type': None,
            'items_total': 0,
            'items_remaining': 0,
            'num_error': 0,
            'num_success': 0,
            'num_exported': 0,
            'step': "STARTING",
        }
        self.callback = None
        self.init_pulp()
        
    def init_pulp(self):
        # initialize DB
        connection.initialize()

    def export(self):
        raise NotImplementedError()

    def set_callback(self, callback):
        self.callback = callback

    def create_iso(self):
        pass

    def validate_target_path(self):
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)