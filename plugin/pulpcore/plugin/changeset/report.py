from gettext import gettext as _


class ChangeReport:
    """
    Report changes to a repository.

    Attributes:
        action (str): The requested action (ADD|REMOVE).
        content (pulpcore.plugin.Content): The affected content model.
        error (Exception): An exception raised during plan execution.
    """

    # Actions
    ADDED = 'ADD'
    REMOVED = 'REMOVE'

    __slots__ = (
        'action',
        'content',
        'error'
    )

    def __init__(self, action, content):
        """
        Args:
            action (str): The requested action (ADD|REMOVE).
            content (pulpcore.plugin.Content): The affected content model.
        """
        self.action = action
        self.content = content
        self.error = None

    def result(self):
        """
        Get the execution result.
        This **should** be called to ensure that error cases are properly handled.

        Returns:
            pulpcore.plugin.Content: The affected content model.

        Raises:
            ChangeFailed: Any exception raised during plan execution.
        """
        if self.error is None:
            return self.content
        else:
            raise ChangeFailed(str(self.error))


class ChangeFailed(Exception):
    """
    A requested change has failed.
    """

    def __init__(self, reason):
        """
        Args:
            reason (str): The reason the change failed.
        """
        self.reason = reason

    def __str__(self):
        return _('Change Failed. Reason: {r}'.format(r=self.reason))
