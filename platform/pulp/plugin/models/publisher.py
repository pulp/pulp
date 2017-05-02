from pulp.app.models import Publisher as PlatformPublisher


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

    This object is a Django model that inherits from :class: `pulp.app.models.Publisher`
    which provides the platform persistent attributes for a publisher object. Plugin authors can
    add additional persistent publisher data by subclassing this object and adding Django
    fields. We defer to the Django docs on extending this model definition with additional fields.

    Validation is done the Django way, so custom validation can also be added the same as any
    Django model. We defer to the Django docs on adding custom validation to the subclassed
    publisher. If any of the model validation methods are overridden, be sure to call super() so
    the platform can still perform its validation.

    Instantiation and calling of the subclassed plugin Publisher is described in detail in the
    :meth: `Publisher.publish` method.
    """

    def publish(self):
        """
        Perform a publish

        It is expected that plugins wanting to support publish will provide an implementation on the
        subclassed Publisher.

        The model attributes encapsulate all of the information required to publish. This includes
        the platform :class: `pulp.app.models.Publish` base attributes and any custom
        attributes defined by the subclass.

        The model attributes were loaded from the database and then had the user specified override
        config applied on top. Additionally the publisher is read-only and prevents the saving of
        changes to the Publisher instance.

        Instantiation and calling of the publish method by the platform is roughly done with the
        following:

            1. The plugin provides an implementation called WidgetPublisher which subclasses
               Publisher

            2. The user makes a call to publish widget_publisher (say id=10) with some override
               config

            3. The platform loads the saved
                >>> wd = WidgetPublisher.objects.get(id=10)

            4. The platform puts the WidgetPublisher into read-only mode

            5. The override config values are written over the in memory WidgetPublisher

            6. Call the full_clean() method on the Django model for validation

                >>> wd.full_clean()

            7. Call into the publish method

                >>> wd.publish()

        Subclasses are designed to override this default implementation and should not call super().
        """
        raise NotImplementedError()

    class Meta:
        abstract = True
