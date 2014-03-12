# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server.db.model.consumer import Consumer

RSA_PUB = 'rsa_pub'
KEY_QUERY = {RSA_PUB: {'$exists': False}}
KEY_UPDATE = {'$set': {RSA_PUB: None}}

CERTIFICATE = 'certificate'
CRT_QUERY = {CERTIFICATE: {'$exists': True}}
CRT_UPDATE = {'$unset': {CERTIFICATE: 1}}


def migrate(*args, **kwargs):
    """
    - Add the rsa_pub.
    - Remove the certificate.
    """
    collection = Consumer.get_collection()
    collection.update(KEY_QUERY, KEY_UPDATE, multi=True, safe=True)
    collection.update(CRT_QUERY, CRT_UPDATE, multi=True, safe=True)
