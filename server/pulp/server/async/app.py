# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
from celery import Celery
from celery.signals import worker_ready

from pulp.server import initialization
from pulp.server.async import tasks
from pulp.server.async.celery_instance import celery


@worker_ready.connect
def initialize_worker(*args, **kwargs):
    """
    This gets called by Celery when the worker is ready to accept work. It initializes Pulp and runs our
    babysit() function synchronously so that the application is aware of this worker immediately.

    :param args:   unused
    :type  args:   list
    :param kwargs: unused
    :type  kwargs: dict
    """
    initialization.initialize()
    tasks.babysit()
