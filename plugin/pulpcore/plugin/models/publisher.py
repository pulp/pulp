from pulpcore.app.models import Publisher as PlatformPublisher


class Publisher(PlatformPublisher):
    """
    The base Publisher object to publish content

    This is meant to be subclassed by plugin authors as an opportunity to provide plugin-specific
    persistant data attributes and additional validation for those attributes.

    This object is a Django model that inherits from :class: `pulpcore.app.models.Publisher`
    which provides the platform persistent attributes for a publisher object. Plugin authors can
    add additional persistent publisher data by subclassing this object and adding Django
    fields. We defer to the Django docs on extending this model definition with additional fields.

    Validation of the publisher is done at the API level by a plugin defined subclass of
    :class: `pulpcore.plugin.serializers.repository.PublisherSerializer`.
    """

    class Meta:
        abstract = True
