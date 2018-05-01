"""

The ``PendingVersion`` is the primary object used by plugin writers to support the Remote. It is a
declarative interface whereby the plugin writer declares the remote content as `PendingContent` and
their associated `PendingArtifact` objects. The `PendingContent` objects are passed as the
`pending_content` argument to `PendingVersion`.

With this information the ``PendingVersion.apply()`` method will:

* Create the `RepositoryVersion` object
* For each `PendingContent` object:
  * Determine if all associated `PendingArtifact` objects are downloaded. If not download them.
  * Determine if the `PendingContent` object is already saved in the database. If not, save it when
    all `PendingArtifact` objects are downloaded.
  * Ensure the new `RepositoryVersion` is associated with the `ContentUnit`.
* Mark the `RepositoryVersion` as complete

The ``PendingVersion`` object takes a sync_mode argument supporting 'additive' and 'mirror' modes.
In 'additive' mode (the default), `ContentUnit` objects are never removed even if their
corresponding `PendingContent` object was not emitted by `pending_content`. In 'mirror' mode, any
`ContentUnit` associated with the `RepositoryVersion` that did not correspond with an emitted
`ContentUnit` is deleted.

The `PendingContent` is designed for stream processing. It is recommended that the `pending_content`
argument be a generator that yields `PendingContent` objects. For efficiency, yielding the
`PendingContent` units as soon they are known is recommended. Consider the example below.

The PendingVersion is used something like this:

Examples:
    >>>
    >>> from pulpcore.plugin.changeset import (
    >>>     PendingArtifact, PendingContent, PendingVersion)
    >>> from pulpcore.plugin.models import Artifact, Content, Remote, Repository
    >>>
    >>>
    >>> class Thing(Content):
    >>>     pass
    >>>
    >>>
    >>> class ThingRemote(Remote):
    >>>
    >>>     def _pending_content(self):
    >>>         metadata = # <fetched metadata>
    >>>         for item in metadata:
    >>>             # Create a concrete model instance for Thing content
    >>>             # using the (thing) metadata.
    >>>             thing = Thing(...)
    >>>             # Create a pending content instance using the model along with a
    >>>             # pending artifact for each file associated with the content.
    >>>             content = PendingContent(
    >>>                 thing,
    >>>                 artifacts={
    >>>                     PendingArtifact(
    >>>                         Artifact(size=1024, sha256='...'), 'http://..', 'one.img'),
    >>>                     PendingArtifact(
    >>>                         Artifact(size=4888, sha256='...'), 'http://..', 'two.img'),
    >>>                 })
    >>>             yield content
    >>>
    >>>     def sync(self):
    >>>         pending_version = PendingVersion(
    >>>             self, pending_content=self._pending_content, sync_mode='mirror'
    >>>         )
    >>>         repo_version = pending_version.create():
    >>>
"""

from .model import PendingArtifact, PendingContent  # noqa
from .pending_version import PendingVersion  # noqa
