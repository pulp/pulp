"""
Django models for artifact catalogs.
"""
from django.core import validators
from django.db import models
from django.utils.translation import ugettext as _

from pulpcore.app.models import Model, Artifact, Importer


class DownloadCatalog(Model):
    """
    Each :class:`DownloadCatalog` maps an :class:`pulpcore.app.models.content.Artifact` to a URL where
    it is stored remotely and to the :class:`pulpcore.app.models.repository.Importer` which contains
    the network configuration required to access that URL.

    Fields:

        url (models.TextField): The URL used to download the related artifact.

    Relations:

        artifact (pulpcore.app.models.Artifact): The artifact that is expected
            to be present at ``url``.
        importer (pulpcore.app.models.Importer): The importer that contains the
            configuration necessary to access ``url``.

    """
    # Although there is a Django field for URLs based on CharField, there is
    # not technically any limit on URL lengths so it's simplier to allow any
    # length here and let the upstream server deal with the problem of size.
    url = models.TextField(blank=True, validators=[validators.URLValidator])

    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE)
    importer = models.ForeignKey(Importer, on_delete=models.CASCADE)

    def __str__(self):
        """
        Human-readable representation of this model.

        This is helpful for interactive prompts and is used in Django's admin
        interface.
        """

        return _('{artifact} is retrievable at {url} by {importer}'.format(
            artifact=self.artifact, url=self.url, importer=self.importer))
