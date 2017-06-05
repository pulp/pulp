from pulpcore.app.models import Importer as PlatformImporter


class Importer(PlatformImporter):
    """
    The base importer object to sync content.

    This is meant to be subclassed by plugin authors as an opportunity to provide:

    * Plugin specific sync functionality
    * Add persistent data attributes for a plugin importer subclass

    The sync implementation is provided by :meth: `Importer.sync` which provides more details.
    Failing to implement this method will prevent sync functionality for this plugin type.

    This object is a Django model that inherits from :class: `pulpcore.app.models.Importer` which
    provides the platform persistent attributes for an importer object. Plugin authors can add
    additional persistent importer data by subclassing this object and adding Django fields. We
    defer to the Django docs on extending this model definition with additional fields.

    Validation of the importer is done at the API level by a plugin defined subclass of
    :class: `pulpcore.plugin.serializers.repository.ImporterSerializer`.
    """

    def sync(self):
        """
        Perform a sync.

        It is expected that plugins wanting to support sync will provide an implementation on the
        subclassed Importer.

        The model attributes encapsulate all of the information required to sync. This includes the
        platform :class: `pulpcore.app.models.Importer` base attributes and any custom attributes
        defined by the subclass.

        Instantiation and calling of the sync method by the platform is defined by
        :meth: `pulpcore.app.tasks.importer.sync`.

        Subclasses are designed to override this default implementation and should not call super().
        """
        raise NotImplementedError()

    class Meta:
        abstract = True
