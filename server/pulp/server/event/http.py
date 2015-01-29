"""
Forwards events to a HTTP call. The configuration used by this notifier
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

from pulp.server.compat import json, json_util


TYPE_ID = 'http'

_logger = logging.getLogger(__name__)


def handle_event(notifier_config, event):
    # fire the actual http push function off in a separate thread to keep
    # pulp from blocking or deadlocking due to the tasking subsystem

    data = event.data()

    _logger.info(data)

    body = json.dumps(data, default=json_util.default)

    thread = threading.Thread(target=_send_post, args=[notifier_config, body])
    thread.setDaemon(True)
    thread.start()


def _send_post(notifier_config, body):

    # Basic headers
    headers = {'Accept': 'application/json',
               'Content-Type': 'application/json'}

    # Parse the URL for the pieces we need
    if 'url' not in notifier_config or not notifier_config['url']:
        _logger.warn('HTTP notifier configured without a URL; cannot fire event')
        return

    url = notifier_config['url']

    try:
        scheme, empty, server, path = url.split('/', 3)
    except ValueError:
        _logger.warn('Improperly configured post_sync_url: %(u)s' % {'u': url})
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
        _logger.warn('Error response from HTTP notifier: %(e)s' % {'e': error_msg})
    connection.close()


def _create_connection(scheme, server):
    if scheme.startswith('https'):
        connection = httplib.HTTPSConnection(server)
    else:
        connection = httplib.HTTPConnection(server)
    return connection
