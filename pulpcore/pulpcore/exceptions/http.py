from gettext import gettext as _

import http.client

from .base import PulpException

from rest_framework import status
from rest_framework.exceptions import APIException, _get_error_details


class MissingResource(PulpException):
    """"
    Base class for missing resource exceptions.

    Exceptions that are raised due to requests for resources that do not exist should inherit
    from this base class.
    """
    http_status_code = http.client.NOT_FOUND

    def __init__(self, **resources):
        """
        :param resources: keyword arguments of resource_type=resource_id
        :type resources: dict
        """
        super().__init__("PLP0001")
        self.resources = resources

    def __str__(self):
        resources_str = ', '.join('%s=%s' % (k, v) for k, v in self.resources.items())
        msg = _("The following resources are missing: %s") % resources_str
        return msg.encode('utf-8')


class ConflictError(APIException):
    """"
    Conflict exception.

    Exception that is raised when a unique constraint is violated.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = {'name': [_('Conflict with the current state of the target resource.')]}
    default_code = 'conflict'

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code

        # For validation failures, we may collect many errors together,
        # so the details should always be coerced to a list if not already.
        if not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]

        self.detail = _get_error_details(detail, code)
