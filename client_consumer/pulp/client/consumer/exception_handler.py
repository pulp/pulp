import logging
from gettext import gettext as _

from pulp.client.extensions.exceptions import ExceptionHandler, CODE_PERMISSIONS_EXCEPTION


_logger = logging.getLogger(__name__)


class ConsumerExceptionHandler(ExceptionHandler):

    def handle_permission(self, e):
        """
        For this script, the register command is used and requires a valid user
        on the server to authenticate against. This override is used to tailor
        the displayed error message to that behavior.
        """

        msg = _(e.error_message)
        _logger.error(msg)
        self.prompt.render_failure_message(msg)

        return CODE_PERMISSIONS_EXCEPTION
