import logging


_logger = logging.getLogger(__name__)


class Conduit:
    """
    The handler conduit provides handlers to call back
    into the handler framework.
    """

    @property
    def consumer_id(self):
        """
        Get the current consumer ID
        :return: The unique consumer ID of the currently running agent
        :rtype:  str
        """
        raise NotImplementedError()

    def get_consumer_config(self):
        """
        Get the consumer configuration.
        @return: The consumer configuration object.
        @rtype: L{pulp.common.config.Config}
        """
        raise NotImplementedError()

    def update_progress(self, report):
        """
        Report a progress update.
        The content of the progress report is at the discretion of
        the handler.  However, it must be json serializable.
        @param report: A progress report.
        @type report: object
        """
        _logger.info('Progress reported:%s', report)

    def cancelled(self):
        """
        Get whether the current operation has been cancelled.
        :return: True if cancelled, else False
        :rtype: bool
        """
        return False
