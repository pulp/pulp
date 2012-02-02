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

import os
import sys
import traceback

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../common/'))

import mock

import testutil

from pulp.server.db.model.dispatch import TaskResource
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import coordinator
from pulp.server.dispatch.taskqueue import TaskQueue

# coordinator instantiation tests ----------------------------------------------

class CoordinatorInstantiationTests(testutil.PulpTest):

    def test_instantiation(self):
        try:
            coordinator.Coordinator(TaskQueue(0))
        except:
            self.fail(traceback.format_exc())

    def test_bad_task_queue(self):
        self.assertRaises(AssertionError, coordinator.Coordinator, None)

# coordinator base tests -------------------------------------------------------

class CoordinatorTests(testutil.PulpTest):

    def setUp(self):
        super(CoordinatorTests, self).setUp()
        self.coordinator = coordinator.Coordinator(TaskQueue(0))
        self.coordinator.task_queue = mock.Mock() # replace the task queue
        self.collection = TaskResource.get_collection()

    def tearDown(self):
        super(CoordinatorTests, self).tearDown()
        self.coordinator = None
        self.collection.drop()
        self.collection = None

# collision detection data -----------------------------------------------------

bat_cave = 'bat cave'
bat_mobile = 'bat-mobile'
cat_illac = 'cat-illac'
lycra = 'lycra'
utility_belt = 'utility belt'
wayne_manor = 'wayne manor'

BATMAN_RESOURCES = {
    dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
        bat_cave:     [dispatch_constants.RESOURCE_CREATE_OPERATION,
                       dispatch_constants.RESOURCE_READ_OPERATION,
                       dispatch_constants.RESOURCE_UPDATE_OPERATION],
        wayne_manor:  [dispatch_constants.RESOURCE_DELETE_OPERATION],
    },
    dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE: {
        lycra:        [dispatch_constants.RESOURCE_UPDATE_OPERATION],
        utility_belt: [dispatch_constants.RESOURCE_READ_OPERATION],
    },
    dispatch_constants.RESOURCE_CDS_TYPE: {
        bat_mobile:   [dispatch_constants.RESOURCE_CREATE_OPERATION,
                       dispatch_constants.RESOURCE_READ_OPERATION],
        cat_illac:    [dispatch_constants.RESOURCE_READ_OPERATION],
    }
}

ROBIN_RESOURCES = {
    dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
        bat_cave:     [dispatch_constants.RESOURCE_READ_OPERATION,
                       dispatch_constants.RESOURCE_UPDATE_OPERATION],
        wayne_manor:  [dispatch_constants.RESOURCE_READ_OPERATION],
    },
    dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE: {
        lycra:        [dispatch_constants.RESOURCE_CREATE_OPERATION],
        utility_belt: [dispatch_constants.RESOURCE_DELETE_OPERATION],
    },
    dispatch_constants.RESOURCE_CDS_TYPE: {
        bat_mobile:   [dispatch_constants.RESOURCE_READ_OPERATION],
        cat_illac:    [dispatch_constants.RESOURCE_READ_OPERATION],
    }
}

ALFRED_RESOURCES = {
    dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
        bat_cave:     [dispatch_constants.RESOURCE_READ_OPERATION,
                       dispatch_constants.RESOURCE_UPDATE_OPERATION],
        wayne_manor:  [dispatch_constants.RESOURCE_UPDATE_OPERATION],
    },
    dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE: {
        lycra:        [dispatch_constants.RESOURCE_UPDATE_OPERATION],
        utility_belt: [dispatch_constants.RESOURCE_UPDATE_OPERATION],
    },
    dispatch_constants.RESOURCE_CDS_TYPE: {
        bat_mobile:   [dispatch_constants.RESOURCE_READ_OPERATION],
        cat_illac:    [dispatch_constants.RESOURCE_DELETE_OPERATION],
    }
}

CATWOMAN_RESOURCES = {
    dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
        bat_cave:     [dispatch_constants.RESOURCE_DELETE_OPERATION],
        wayne_manor:  [dispatch_constants.RESOURCE_READ_OPERATION],
    },
    dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE: {
        lycra:        [dispatch_constants.RESOURCE_DELETE_OPERATION],
        utility_belt: [dispatch_constants.RESOURCE_UPDATE_OPERATION],
    },
    dispatch_constants.RESOURCE_CDS_TYPE: {
        bat_mobile:   [dispatch_constants.RESOURCE_READ_OPERATION],
        cat_illac:    [dispatch_constants.RESOURCE_CREATE_OPERATION,
                       dispatch_constants.RESOURCE_UPDATE_OPERATION],
    }
}

# collision detection tests ----------------------------------------------------

class CoordinatorCollisionDetectionTests(CoordinatorTests):

    pass
