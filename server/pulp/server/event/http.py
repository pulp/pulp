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

from pulp.server.compat import json, json_util

from requests import post
from requests.auth import HTTPBasicAuth


TYPE_ID = 'http'

_logger = logging.getLogger(__name__)


def handle_event(notifier_config, event):
    # fire the actual http push function off in a separate thread to keep
    # pulp from blocking or deadlocking due to the tasking subsystem
    json_body = json.dumps(event.data(), default=json_util.default)
    _logger.info(json_body)
    _send_post(notifier_config, json_body)


def _send_post(notifier_config, json_body):
    """
    Sends a POST request with the given data to the configured notifier url.

    :param notifier_config: The configuration for the HTTP notifier. This should
                            contain the 'url' key, and optional 'username' and
                            'password' keys.
    :type notifier_config:  dict
    :param json_body:       The POST data that has been serialized to JSON.
    :param json_body:       dict
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

    try:
        response = post(url, data=json_body, auth=auth,
                        headers={'Content-Type': 'application/json'}, timeout=15)
    except Exception:
        _logger.exception("HTTP Notification Failed")
        return

    if response.status_code != 200:
        _logger.error(_('Received HTTP {code} from HTTP notifier to {url}.').format(
            code=response.status_code, url=url))
