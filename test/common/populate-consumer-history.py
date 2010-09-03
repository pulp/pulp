#!/usr/bin/python
#
# Pulp Registration and subscription module
# Copyright (c) 2010 Red Hat, Inc.
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

# Python
import datetime
import os
import sys

# 3rd Party
import pymongo

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.insert(0, srcdir)

import pulp.server.api.consumer_history as history
from pulp.server.db.connection import get_object_db
from pulp.server.db.model import ConsumerHistoryEvent

EVENTS = []

CONSUMER_ID = 'jdob'

event = ConsumerHistoryEvent(CONSUMER_ID, 'consumer', history.TYPE_CONSUMER_CREATED, None)
EVENTS.append(event)

event = ConsumerHistoryEvent(CONSUMER_ID, 'consumer', history.TYPE_REPO_BOUND, {'repo_id': 'repo1'})
EVENTS.append(event)
event = ConsumerHistoryEvent(CONSUMER_ID, 'consumer', history.TYPE_REPO_BOUND, {'repo_id': 'repo2'})
EVENTS.append(event)
event = ConsumerHistoryEvent(CONSUMER_ID, 'consumer', history.TYPE_REPO_BOUND, {'repo_id': 'repo3'})
EVENTS.append(event)

event = ConsumerHistoryEvent(CONSUMER_ID, 'consumer', history.TYPE_REPO_BOUND, {'repo_id': 'repo1'})
event.timestamp = datetime.datetime.now() - datetime.timedelta(days=365)
EVENTS.append(event)

def db():
    return get_object_db('consumer_history', [], [])

def clean():
    db().remove(safe=True)

def populate():
    db_conn = db()

    for event in EVENTS:
        db_conn.insert(event)

if __name__ == '__main__':
    populate()
    