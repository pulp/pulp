"""
The content-guard registry maps content-guard logic to
ContentGuard model classes.

Examples:
    Registering content-guard (logic) using the decorator:
    >>>
    >>> @contentguard(model=MyGuardModel)
    >>> def permit(request, content_guard)
    >>>     if not authorized:
    >>>         raise PermissionError()
    >>>
    The decorated function must accept a request and a content_guard
    argument.  It must raise PermissionError when the request is
    not authorized.
"""

import logging

from gettext import gettext as _


log = logging.getLogger(__name__)


class ContentGuardRegistry:
    """
    Content guard (logic) registry.

    Maps content-guard logic to ContentGuard model (class) when used as
    a decorator. Provides authorization API.

    Attributes:
        model (pulpcore.app.models.ContentGuard): A concrete content-guard model (class).
    """

    functions = {}

    @classmethod
    def permit(cls, request, distribution):
        """
        Authorize a request using the specified content-guard.

        Args:
            request (django.http.HttpRequest): A request for content.
            distribution (pulpcore.app.models.Distribution): A content distribution.

        Raises:
            PermissionError: When not authorized or the content-guard has
                not been registered.
        """
        content_guard = distribution.content_guard
        if not content_guard:
            return
        content_guard = content_guard.cast()
        try:
            permit = cls.functions[type(content_guard)]
        except KeyError:
            description = _('{g} not found.').format(g=content_guard)
            log.error(description)
            raise PermissionError(distribution)
        else:
            permit(request, content_guard)

    def __init__(self, model):
        """
        Args:
            model (pulpcore.app.models.ContentGuard): A content-guard model (class).
        """
        self.model = model

    def __call__(self, fn):
        """
        Args:
            fn (function): A decorated function.
        """
        self.functions[self.model] = fn
        return fn


# decorator
contentguard = ContentGuardRegistry
