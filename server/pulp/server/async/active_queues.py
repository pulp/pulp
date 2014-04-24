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

"""
This module imports the celery app from pulp_celery, and inspects the active_queues.

Normally, this code would be called from inside the babysit() task, however the use of
active_queues inside a celery task causes errors to occur.  Tasks run in a child processes that has
already been forked by celery, but qpid.messaging is not fork safe since the connection of the
parent process is shared by the child process.

This module is designed to be run as a script.  Since this script will run in a fresh python
interpreter using subprocessBy calling out to a fresh python interpreter using subprocess, the
issue is avoided because the new process does not have a reference to any of the existing
connections.

The results from active_queues() is a Python object, which needs to be written to stdout.  To do
this correctly, it needs to be serialized to json first.
"""

import json
import sys

from pulp.server.async.celery_instance import celery as pulp_celery

from celery.app import control
controller = control.Control(app=pulp_celery)


def print_active_queues():
    """Print the active queue data as json to stdout."""
    active_queues = controller.inspect().active_queues()
    json_output = json.dumps(active_queues)
    sys.stdout.write(json_output)


if __name__ == '__main__':
    print_active_queues()
