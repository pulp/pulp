"""

The ``ChangeSet`` is the primary object used by plugin writers to support the Importer.
It represents a set of changes to be made to the repository in terms of content
that needs to be added (additions) and content that needs to be removed (removals).
The term `remote` is used to describe the repository that the importer is synchronizing
with.  The term ``PendingContent`` is content contained in the remote repository.

Plugin writers need to pass `additions` to the `ChangeSet` as a collection of
`PendingContent`.  In other words, `additions` are a collection of content in the remote
repository that is not in the (local) Pulp repository and it needs to be added.

Plugin writers need to pass `removals` to the `ChangeSet` as a collection of `Content`
that has been fetched from the Pulp DB.  In other words, `removals` are a collection
content that is in the Pulp (local) repository that is not in the remote repository.
Or, content that needs to be removed for any reason as determined by the importer.

The `ChangeSet` is designed for `stream` processing.  It is strongly encouraged that both
the `additions` and `removals` be a `generator` that is wrapped in a ``SizedIterable``.
Wrapping the generator in a `SizedIterable` provides the total number of items that the
generator will yield.  This is needed for progress reporting.

Once the `ChangeSet` is constructed, the `apply()` method is called which returns an
iterator of ``ChangeReport``.  Due to the `streams processing` design of the `ChangeSet`,
the returned iterator **must** be iterated for work to be performed.  The `ChangeReport`
contains:

- The requested action (ADD|REMOVE).
- The content (model) instance that was added/removed.
- A list of any exceptions raised.

The ChangeSet is used something like this:

Examples:
    >>>
    >>> from django.db.models import Q
    >>> from collections import namedtuple
    >>> from pulpcore.plugin.changeset import (
    >>>     ChangeSet, PendingArtifact, PendingContent, SizedIterable)
    >>> from pulpcore.plugin.models import Artifact, Content, Importer, Repository
    >>>
    >>>
    >>> Delta = namedtuple('Delta', ['additions', 'removals'])
    >>>
    >>>
    >>> class Thing(Content):
    >>>     pass
    >>>
    >>>
    >>> class ThingImporter(Importer):
    >>>
    >>>     def _build_additions(self, delta, metadata):
    >>>         # Using the set of additions defined by the delta and the metadata,
    >>>         # build and yield the content that needs to be added.
    >>>
    >>>         for item in metadata:
    >>>             # Needed?
    >>>             if not item.natural_key in delta.additions:
    >>>                 continue
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
    >>>     def _fetch_removals(self, delta):
    >>>         # Query the DB and yield any content in the repository
    >>>         # matching the natural key in the delta.
    >>>         for natural_keys in BatchIterator(delta.removals):
    >>>             q = Q()
    >>>             for key in natural_keys:
    >>>                 q |= Q(...)
    >>>             q_set = self.repository.content.filter(q)
    >>>             q_set = q_set.only('artifacts')
    >>>             for content in q_set:
    >>>                 yield content
    >>>
    >>>     def _find_delta(self, metadata, inventory):
    >>>         # Using the metadata and inventory (of content in the repository),
    >>>         # determine the set of content that needs to be added and the set of
    >>>         # content that needs to be removed.
    >>>         remote = set()
    >>>         for thing in metadata:
    >>>             remote.add(thing.natural_key())
    >>>             additions = remote - inventory
    >>>             removals = inventory - remote
    >>>         return Delta(additions=additions, removals=removals)
    >>>
    >>>     def _fetch_inventory(self):
    >>>         # Query the DB and find all `Thing` content in the repository.
    >>>         # The `inventory` is used for comparison and should only be the natural
    >>>         # key for each content.
    >>>         inventory = set()
    >>>         q_set = Thing.objects.filter(repositories=self.repository)
    >>>         q_set = q_set.only(*Thing.natural_key_fields())
    >>>         for content in (c.cast() for c in q_set):
    >>>             inventory.add(content.natural_key())
    >>>         return inventory
    >>>
    >>>     def _build_changeset(self):
    >>>         # Build a changeset.
    >>>         metadata = # <fetched metadata>
    >>>         inventory = self._fetch_inventory()
    >>>         delta = self.find_delta(metadata, inventory)
    >>>         additions = SizedIterable(
    >>>             self._build_additions(delta, metadata),
    >>>             len(delta.additions))
    >>>         removals = SizedIterable(
    >>>             self._fetch_removals(delta),
    >>>             len(delta.removals))
    >>>         return ChangeSet(self, additions=additions, removals=removals)
    >>>
    >>>     def sync(self):
    >>>         changeset = self._build_changeset()
    >>>         for report in changeset.apply():
    >>>             try:
    >>>                 report.result()
    >>>             except ChangeFailed:
    >>>                 # Failed
    >>>             else:
    >>>                 # Succeeded
    >>>
"""

from .iterator import BatchIterator  # noqa
from .main import ChangeSet, SizedIterable  # noqa
from .model import PendingArtifact, PendingContent  # noqa
from .report import ChangeReport, ChangeFailed  # noqa
