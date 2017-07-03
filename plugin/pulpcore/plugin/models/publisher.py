from pulpcore.app.models import Publisher as PlatformPublisher


class Publisher(PlatformPublisher):
    """
    The base Publisher object to publish content

    This is meant to be subclassed by plugin authors as an opportunity to provide:

    * Plugin specific publish functionality
    * Add persistent data attributes for a plugin publisher subclass
    * Additional validation of plugin publisher subclass configuration

    The publish implementation is provided by :meth: `Publisher.publish` which provides more
    details. Failing to implement this method will prevent publish functionality for this plugin
    type.

    This object is a Django model that inherits from :class: `pulpcore.app.models.Publisher`
    which provides the platform persistent attributes for a publisher object. Plugin authors can
    add additional persistent publisher data by subclassing this object and adding Django
    fields. We defer to the Django docs on extending this model definition with additional fields.

    Validation of the publisher is done at the API level by a plugin defined subclass of
    :class: `pulpcore.plugin.serializers.repository.PublisherSerializer`.
    """

    def publish(self):
        """
        Perform a publish.

        It is expected that plugins wanting to support publish will provide an implementation on the
        subclassed Publisher.

        The model attributes encapsulate all of the information required to publish. This includes
        the platform :class: `pulpcore.app.models.Publisher` base attributes and any custom
        attributes defined by the subclass.

        Instantiation and calling of the publish method by the platform is defined by
        :meth: `pulpcore.app.tasks.publisher.publish`.

        Subclasses are designed to override this default implementation and should not call super().
        """
        raise NotImplementedError()

    class Meta:
        abstract = True
