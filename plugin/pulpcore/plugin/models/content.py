from pulpcore.app import models


class ContentGuard(models.ContentGuard):
    """
    Defines a named content guard.

    This is meant to be subclassed by plugin authors as an opportunity to provide
    plugin-specific persistent attributes and additional validation for those attributes.
    The permit() method must be overridden to provide the web request authorization logic.

    This object is a Django model that inherits from :class: `pulpcore.app.models.ContentGuard`
    which provides the platform persistent attributes for a content-guard. Plugin authors can
    add additional persistent attributes by subclassing this class and adding Django fields.
    We defer to the Django docs on extending this model definition with additional fields.
    """

    class Meta:
        abstract = True

    def permit(self, request):
        """
        Authorize the specified web request.

        Args:
            request (django.http.HttpRequest): A request for a published file.

        Raises:
            PermissionError: When not authorized.
        """
        raise NotImplementedError()
