import logging
import smtplib
import threading

try:
    from email.mime.text import MIMEText
except ImportError:
    # python 2.4 version
    from email.MIMEText import MIMEText

from pulp.server.compat import json, json_util
from pulp.server.config import config


TYPE_ID = 'email'
_logger = logging.getLogger(__name__)


def handle_event(notifier_config, event):
    """
    If email is enabled in the server settings, sends an email to each recipient
    listed in the notifier_config.

    :param notifier_config: dictionary with keys 'subject', which defines the
                            subject of each email message, and 'addresses',
                            which is a list of strings that are email addresses
                            that should receive this notification.
    :type  notifier_config: dict
    :param event:   Event instance
    :type  event:   pulp.server.event.data.event
    :return: None
    """
    if not config.getboolean('email', 'enabled'):
        return
    body = json.dumps(event.data(), indent=2, default=json_util.default)
    subject = notifier_config['subject']
    addresses = notifier_config['addresses']

    for address in addresses:
        thread = threading.Thread(target=_send_email, args=(subject, body, address))
        thread.daemon = True
        thread.start()


def _send_email(subject, body, to_address):
    """
    Send a text email to one recipient

    :param subject: email subject
    :type  subject: basestring
    :param body:    text body of the email
    :type  body:    basestring
    :param to_address:  email address to send to
    :type  to_address:  basestring

    :return: None
    """
    host = config.get('email', 'host')
    port = config.getint('email', 'port')
    from_address = config.get('email', 'from')

    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = from_address
    message['To'] = to_address

    try:
        connection = smtplib.SMTP(host=host, port=port)
    except smtplib.SMTPConnectError:
        _logger.exception('SMTP connection failed to %s on %s' % (host, port))
        return

    try:
        connection.sendmail(from_address, to_address, message.as_string())
    except smtplib.SMTPException:
        try:
            _logger.exception('Error sending mail.')
        except AttributeError:
            _logger.error('SMTP error while sending mail')
    connection.quit()
