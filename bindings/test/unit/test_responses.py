# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
"""
This module contains tests on the pulp.bindings.responses module.
"""
import unittest


class TestTask(unittest.TestCase):
    """
    This class contains tests on the Task object.
    """
    def test___init__(self):
        """
        Test the __init__() method with some typical data.
        """
        some_typical_data = {
            '_href': '/pulp/api/v2/tasks/34ba67fb-dbf9-4599-9966-5bded37de689/',
            'task_id': u'34ba67fb-dbf9-4599-9966-5bded37de689',
            'tags': ['pulp:repository:pulp-stable-f18', 'pulp:action:sync'],
            '_ns': 'task_status',
            'start_time': 1391205392,
            'progress_report': {'some': 'data structure'},
            'queue': 'reserved_resource_worker-0@lemonade.rdu.redhat.com',
            'state': 'running',
            '_id': {'$oid': '52ec1c0f527c8e6c4749e419'}}
