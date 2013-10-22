# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from datetime import datetime
from unittest import TestCase

from mock import patch

from pulp.common import dateutils
from pulp.server.webservices.serialization import content
from pulp.server.webservices.serialization import db

LAST_UPDATED = '_last_updated'


class TestSerialization(TestCase):

    @patch('pulp.server.webservices.serialization.db.scrub_mongo_fields',
           wraps=db.scrub_mongo_fields)
    def test_serialization(self, mock):
        dt = datetime(2012, 10, 24, 10, 20, tzinfo=dateutils.utc_tz())
        last_updated = dateutils.datetime_to_utc_timestamp(dt)
        unit = {'_last_updated': last_updated}
        serialized = content.content_unit_obj(unit)
        mock.assert_called_once_with(unit)
        self.assertTrue(LAST_UPDATED in serialized)
        self.assertEqual(serialized[LAST_UPDATED], '2012-10-24T10:20:00Z')

    def test_serialization_no_last_modified(self):
        serialized = content.content_unit_obj({})
        self.assertFalse(LAST_UPDATED in serialized)