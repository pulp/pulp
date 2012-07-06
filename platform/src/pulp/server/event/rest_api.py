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
Forwards events to a REST API call. The configuration used by this notifier
is as follows:

url
  Full URL to contact with the event data. A POST request will be made to this
  URL with the contents of the events in the body.

Eventually this should be enhanced to support authentication credentials as well.
"""

import base64
import httplib
import logging
import threading

from pulp.server.compat import json

# -- constants ----------------------------------------------------------------

TYPE_ID = 'rest-api'

LOG = logging.getLogger(__name__)

# -- framework hook -----------------------------------------------------------

def handle_event(notifier_config, event):
    # fire the actual http push function off in a separate thread to keep
    # pulp from blocking or deadlocking due to the tasking subsystem

    data = {
        'event_type' : event.event_type,
        'payload' : event.payload,
    }

    LOG.info(data)

    body = json.dumps(data)

    thread = threading.Thread(target=_send_post, args=[notifier_config, body])
    thread.setDaemon(True)
    thread.start()

# -- private ------------------------------------------------------------------

def _send_post(notifier_config, body):

    # Basic headers
    headers = {'Accept': 'application/json',
               'Content-Type': 'application/json'}

    # Parse the URL for the pieces we need
    url = notifier_config['url']
    if not url:
        LOG.warn('REST API notifier configured without a URL; cannot fire event')
        return

    try:
        scheme, empty, server, path = url.split('/', 3)
    except ValueError:
        LOG.warn('Improperly configured post_sync_url: %(u)s' % {'u': url})
        return

    connection = _create_connection(scheme, server)

    # Process authentication
    if 'username' in notifier_config and 'password' in notifier_config:
        raw = ':'.join((notifier_config['username'], notifier_config['password']))
        encoded = base64.encodestring(raw)[:-1]
        headers['Authorization'] = 'Basic ' + encoded

    connection.request('POST', '/' + path, body=body, headers=headers)
    response = connection.getresponse()
    if response.status != httplib.OK:
        error_msg = response.read()
        LOG.warn('Error response from REST API notifier: %(e)s' % {'e': error_msg})
    connection.close()

def _create_connection(scheme, server):
    if scheme.startswith('https'):
        connection = httplib.HTTPSConnection(server)
    else:
        connection = httplib.HTTPConnection(server)
    return connection
