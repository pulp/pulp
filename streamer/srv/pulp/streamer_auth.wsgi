from gettext import gettext as _
import logging

from pulp.server.config import config
from pulp.server.lazy.url import SignedURL, NotValid, Key
from pulp.server.logs import start_logging

start_logging()
log = logging.getLogger(__name__)

key_path = config.get('authentication', 'rsa_pub')
key = Key.load(key_path)


def allow_access(environ, host):
    """
    Implements the WSGI host access control interface. This method
    checks the signature on the URL to see if the request has been
    approved by the Pulp server.

    :param environ: The 'environ' dictionary passed as first argument
                    is a cut down version of what would be supplied to
                    the actual WSGI application. This includes the
                    'wsgi.errors' object for the purposes of logging
                    error messages associated with the request.
    :type  environ: dict
    :param host:    The host requesting access (not used).
    :type  host:    str

    :return: True if the given host is allowed access, False otherwise.
    :rtype:  bool
    """
    url = SignedURL(environ['REQUEST_URI'])
    try:
        url.validate(key)
        log.debug(_('Validated {ip} for {url}.').format(ip=environ['REMOTE_ADDR'], url=url))
        return True
    except NotValid, le:
        msg = _('Received invalid request from {ip} for {url}: {error}.')
        log.debug(msg.format(ip=environ['REMOTE_ADDR'], url=url, error=str(le)))
        return False
