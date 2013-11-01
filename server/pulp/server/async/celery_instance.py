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
Due to our factory, we cannot put the instantiation of the Celery application into our app.py
module, as it will lead to circular dependencies since tasks.py also need to import this object, and
the factory ends up importing tasks.py when it imports all the managers.

Hopefully we will eliminate the factory in the future, but until then this workaround is necessary.
"""
from celery import Celery

from pulp.server.config import config


broker_url = config.get('tasks', 'broker_url')
celery = Celery('tasks', backend='amqp', broker=broker_url)
