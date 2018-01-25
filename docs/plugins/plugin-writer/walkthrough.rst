Plugin Writing Walkthrough
==========================

For a complete list of what should be done to have a working plugin, check :doc:`checklist`.
In this section key parts of plugin implementation are covered in more detail to help you as
a plugin writer to get started.

In addition, `the Plugin template <https://github.com/pulp/plugin_template>`_ can be used to help
with plugin layout and stubs for necessary classes. This guide assumes that you have used the
template to bootstrap your plugin.

# TODO(asmacdo) Write here a walkthrough of implementing the models
# TODO(asmacdo) Instruct plugin writer to read models.rst in contributor docs

.. _understanding-models:


Define your plugin Content type
-------------------------------

To define a new content type(s), e.g. ``ExampleContent``:

* :class:`pulpcore.plugin.models.Content` should be subclassed and extended with additional
  attributes to the plugin needs,
* define ``TYPE`` class attribute which is used for filtering purposes,
* uniqueness should be specified in ``Meta`` class of newly defined ``ExampleContent`` model,
* ``unique_together`` should be specified for the ``Meta`` class of ``ExampleContent`` model,
* create a serializer for your new Content type as a subclass of
  :class:`pulpcore.plugin.serializers.ContentSerializer`,
* create a viewset for your new Content type as a subclass of
  :class:`pulpcore.plugin.viewsets.ContentViewSet`

:class:`~pulpcore.plugin.models.Content` model should not be used directly anywhere in plugin code.
Only plugin-defined Content classes are expected to be used.

Check ``pulp_example`` implementation of `the ExampleContent
<https://github.com/pulp/pulp_example/blob/master/pulp_example/app/models.py#L87-L114>`_ and its
`serializer <https://github.com/pulp/pulp_example/blob/master/pulp_example/app/serializers.py#L7-L13>`_
and `viewset <https://github.com/pulp/pulp_example/blob/master/pulp_example/app/viewsets.py#L13-L17>`_.
For a general reference for serializers and viewsets, check `DRF documentation
<http://www.django-rest-framework.org/api-guide/viewsets/>`_.


.. _define-importer:

Define your plugin Importer
---------------------------

To define a new importer, e.g. ``ExampleImporter``:

* :class:`pulpcore.plugin.models.Importer` should be subclassed and extended with additional
  attributes to the plugin needs,
* define ``TYPE`` class attribute which is used for filtering purposes,
* create a serializer for your new importer as a subclass of
  :class:`pulpcore.plugin.serializers.ImporterSerializer`,
* create a viewset for your new importer as a subclass of
  :class:`pulpcore.plugin.viewsets.ImporterViewSet`.

:class:`~pulpcore.plugin.models.Importer` model should not be used directly anywhere in plugin
code, except as the parent class to the plugin importer. Only plugin-defined Importer classes are
expected to be used.

There are several important aspects relevant to importer implementation which were briefly mentioned
# TODO(asmacdo) update to models.rst
in the :ref:`understanding-models` section:

# TODO(asmacdo) responsibility of changeset?
# TODO(asmacdo) I think this whole section should be removed, and placed in a separate guide for
updating content without ChangeSets.
* due to deduplication of :class:`~pulpcore.plugin.models.Content` and
  :class:`~pulpcore.plugin.models.Artifact` data, the importer needs to
  fetch and use them when they already exist.
* :class:`~pulpcore.plugin.models.ContentArtifact` associates
  :class:`~pulpcore.plugin.models.Content` and :class:`~pulpcore.plugin.models.Artifact`. If
  :class:`~pulpcore.plugin.models.Artifact` is not downloaded yet,
  :class:`~pulpcore.plugin.models.ContentArtifact` contains ``NULL`` value for
  :attr:`~pulpcore.plugin.models.ContentArtifact.artifact`. It should be updated whenever
  corresponding :class:`~pulpcore.plugin.models.Artifact` is downloaded.
# TODO(asmacdo) </end removable section>

# TODO(mention the low level docs section, but introduce changeset as "the way"
The importer implementation suggestion above allows plugin writer to have an understanding and
control at a low level.
The plugin API has a higher level, more simplified, API which introduces the concept of
:class:`~pulpcore.plugin.changeset.ChangeSet`.
It allows plugin writer:

* to specify a set of changes (which :class:`~pulpcore.plugin.models.Content` to add or to remove)
  to be made to a repository
* apply those changes (add to a repository, remove from a repository, download files if needed)

Check :ref:`documentation and detailed examples <changeset-docs>` for the
:class:`~pulpcore.plugin.changeset.ChangeSet` as well as `the implementation of File plugin importer
<https://github.com/pulp/pulp_file/blob/master/pulp_file/app/models.py#L72-L224>`_ which uses it.

.. _define-publisher:

Define your sync task
---------------------
# TODO(asmacdo)
* ``sync`` method should be defined on a plugin importer model ``ExampleImporter``,

One of the ways to perform synchronization:

* Download and analyze repository metadata from a remote source.
* Decide what needs to be added to repository or removed from it.
* Associate already existing content to a repository by creating an instance of
  :class:`~pulpcore.plugin.models.RepositoryContent` and saving it.
* Remove :class:`~pulpcore.plugin.models.RepositoryContent` objects which were identified for
  removal.
* For every content which should be added to Pulp create but do not save yet:

  * instance of ``ExampleContent`` which will be later associated to a repository.
  * instance of :class:`~pulpcore.plugin.models.ContentArtifact` to be able to create relations with
    the artifact models.
  * instance of :class:`~pulpcore.plugin.models.RemoteArtifact` to store information about artifact
    from remote source and to make a relation with :class:`~pulpcore.plugin.models.ContentArtifact`
    created before.

* If a remote content should be downloaded right away (aka ``immediate`` download policy), use
  the suggested  :ref:`downloading <download-docs>` solution. If content should be downloaded
  later (aka ``on_demand`` or ``background`` download policy), feel free to skip this step.
* Save all artifact and content data in one transaction:

  * in case of downloaded content, create an instance of
    :class:`~pulpcore.plugin.models .Artifact`. Set the `file` field to the
    absolute path of the downloaded file. Pulp will move the file into place
    when the Artifact is saved. The Artifact refers to a downloaded file on a
    filesystem and contains calculated checksums for it.
  * in case of downloaded content, update the :class:`~pulpcore.plugin.models.ContentArtifact` with
    a reference to the created :class:`~pulpcore.plugin.models.Artifact`.
  * create and save an instance of the :class:`~pulpcore.plugin.models.RepositoryContent` to
    associate the content to a repository.
  * save all created artifacts and content: ``ExampleContent``,
    :class:`~pulpcore.plugin.models.ContentArtifact`,
    :class:`~pulpcore.plugin.models.RemoteArtifact`.

* Use :class:`~pulpcore.plugin.models.ProgressBar` to report the progress of some steps if needed.



Define your plugin Publisher
----------------------------

To define a new publisher, e.g. ``ExamplePublisher``:

* :class:`pulpcore.plugin.models.Publisher` should be subclassed and extended with additional
  attributes to the plugin needs,
* define ``TYPE`` class attribute which is used for filtering purposes,
* create a serializer for your new publisher a subclass of
  :class:`pulpcore.plugin.serializers.PublisherSerializer`,
* create a viewset for your new publisher as a subclass of
  :class:`pulpcore.plugin.viewsets.PublisherViewSet`.

:class:`~pulpcore.plugin.models.Publisher` model should not be used directly anywhere in plugin
code. Only plugin-defined Publisher classes are expected to be used.

# TODO(asmacdo) change to pulp_file
Check ``pulp_example`` implementation of `the ExamplePublisher
<https://github.com/pulp/pulp_example/blob/master/pulp_example/app/models.py#L117-L181>`_.

Define your publish task
------------------------
# TODO(asmacdo)
One of the ways to perform publishing:

* Find :class:`~pulpcore.plugin.models.ContentArtifact` objects which should be published
* For each of them create and save instance of :class:`~pulpcore.plugin.models.PublishedArtifact`
  which refers to :class:`~pulpcore.plugin.models.ContentArtifact` and
  :class:`~pulpcore.app.models.Publication` to which this artifact belongs.
* Generate and write to a disk repository metadata
* For each of the metadata objects create and save  instance of
  :class:`~pulpcore.plugin.models.PublishedMetadata` which refers to a corresponding file and
  :class:`~pulpcore.app.models.Publication` to which this metadata belongs.
* Use :class:`~pulpcore.plugin.models.ProgressBar` to report progress of some steps if needed.

