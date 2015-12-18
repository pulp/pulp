"""
Forwards events to a HTTP call. The configuration used by this notifier
is as follows:

url
  Full URL to contact with the event data. A POST request will be made to this
  URL with the contents of the events in the body.

Eventually this should be enhanced to support authentication credentials as well.
"""
from gettext import gettext as _
import logging
import threading

from requests import post
from requests.auth import HTTPBasicAuth


TYPE_ID = 'http'

_logger = logging.getLogger(__name__)


def handle_event(notifier_config, event):
    # fire the actual http push function off in a separate thread to keep
    # pulp from blocking or deadlocking due to the tasking subsystem
    data = event.data()
    _logger.info(data)
    thread = threading.Thread(target=_send_post, args=[notifier_config, data])
    thread.setDaemon(True)
    thread.start()


def _send_post(notifier_config, data):
    """
    Sends a POST request with the given data to the configured notifier url.

    :param notifier_config: The configuration for the HTTP notifier. This should
                            contain the 'url' key, and optional 'username' and
                            'password' keys.
    :type notifier_config:  dict
    :param data:            The POST data as a Python dictionary.
    :param data:            dict
    """
    if 'url' not in notifier_config or not notifier_config['url']:
        _logger.error(_('HTTP notifier configured without a URL; cannot fire event'))
        return
    url = notifier_config['url']

    # Process authentication
    if 'username' in notifier_config and 'password' in notifier_config:
        auth = HTTPBasicAuth(notifier_config['username'], notifier_config['password'])
    else:
        auth = None

    response = post(url, data=data, auth=auth)
    if response.status_code != 200:
        _logger.error(_('Received HTTP {code} from HTTP notifier to {url}.').format(
            code=response.status_code, url=url))
