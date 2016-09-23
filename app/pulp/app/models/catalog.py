"""
Django models for artifact catalogs.
"""
from django.core import validators
from django.db import models
from django.utils.translation import ugettext as _

from pulp.app.models import Model, Artifact, Importer


class DownloadCatalog(Model):
    """
    Each :class:`DownloadCatalog` maps an :class:`Artifact` to a URL where
    it is stored remotely and to the :class:`Importer` which contains the
    network configuration required to access that URL.

    Fields:

    :cvar url: The URL used to download the related artifact.
    :type url: django.db.models.TextField

    Relations:

    :cvar artifact: The artifact that is expected to be present at ``url``.
    :type artifact: pulp.app.models.Artifact

    :cvar importer: The importer that contains the configuration necessary
                    to access ``url``.
    :type importer: pulp.app.models.Importer
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
