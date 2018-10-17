Writing Your First Plugin
=========================

For a complete list of what should be done to have a working plugin, check :doc:`checklist`.
In this section key parts of plugin implementation are covered in more detail to help you as
a plugin writer to get started.

In addition, `the Plugin template <https://github.com/pulp/plugin_template>`_ can be used to help
with plugin layout and stubs for necessary classes.

.. _understanding-models:

Understanding models
--------------------
There are models which are expected to be used in plugin implementation, so understanding what they
are designed for is useful for a plugin writer. Each model below has a link to its documentation
where its purpose, all attributes and relations are listed.

Here is a gist of how models are related to each other and what each model is responsible for.

* :class:`~pulpcore.app.models.Repository` contains :class:`~pulpcore.plugin.models.Content`.
  :class:`~pulpcore.plugin.models.RepositoryContent` is used to represent this relation.
* :class:`~pulpcore.plugin.models.Content` can have :class:`~pulpcore.plugin.models.Artifact`
  associated with it. :class:`~pulpcore.plugin.models.ContentArtifact` is used to represent this
  relation.
* :class:`~pulpcore.plugin.models.ContentArtifact` can have
  :class:`~pulpcore.plugin.models.RemoteArtifact` associated with it.
* :class:`~pulpcore.plugin.models.Artifact` is a file.
* :class:`~pulpcore.plugin.models.RemoteArtifact` contains information about
  :class:`~pulpcore.plugin.models.Artifact` from a remote source, including URL to perform
  download later at any point.
* :class:`~pulpcore.plugin.models.Remote` knows specifics of the plugin
  :class:`~pulpcore.plugin.models.Content` to put it into Pulp.
  :class:`~pulpcore.plugin.models.Remote` defines how to synchronize remote content. Pulp
  Platform provides support for concurrent  :ref:`downloading <download-docs>` of remote content.
  Plugin writer is encouraged to use one of them but is not required to.
* :class:`~pulpcore.plugin.models.PublishedArtifact` refers to
  :class:`~pulpcore.plugin.models.ContentArtifact` which is published and belongs to a certain
  :class:`~pulpcore.app.models.Publication`.
* :class:`~pulpcore.plugin.models.PublishedMetadata` is a repository metadata which is published,
  located in ``/var/lib/pulp/published`` and belongs to a certain
  :class:`~pulpcore.app.models.Publication`.
* :class:`~pulpcore.plugin.models.Publisher` knows specifics of the plugin
  :class:`~pulpcore.plugin.models.Content` to make it available outside of Pulp.
  :class:`~pulpcore.plugin.models.Publisher` defines how to publish content available in Pulp.
* :class:`~pulpcore.app.models.Publication` is a result of publish operation of a specific
  :class:`~pulpcore.plugin.models.Publisher`.
* :class:`~pulpcore.app.models.Distribution` defines how a publication is distributed for a specific
  :class:`~pulpcore.plugin.models.Publisher`.
* :class:`~pulpcore.plugin.models.ProgressBar` is used to report progress of the task.


An important feature of the current design is deduplication of
:class:`~pulpcore.plugin.models.Content` and :class:`~pulpcore.plugin.models.Artifact` data.
:class:`~pulpcore.plugin.models.Content` is shared between :class:`~pulpcore.app.models.Repository`,
:class:`~pulpcore.plugin.models.Artifact` is shared between
:class:`~pulpcore.plugin.models.Content`.
See more details on how it affects remote implementation in :ref:`define-remote` section.


Check ``pulp_file`` `implementation <https://github.com/pulp/pulp_file/>`_ to see how all
those models are used in practice.
More detailed explanation of model usage with references to ``pulp_file`` code is below.


.. _define-content-type:

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

Check ``pulp_file`` implementation of `the FileContent
<https://github.com/pulp/pulp_file/blob/master/pulp_file/app/models.py>`_ and its
`serializer <https://github.com/pulp/pulp_file/blob/master/pulp_file/app/serializers.py>`_
and `viewset <https://github.com/pulp/pulp_file/blob/master/pulp_file/app/viewsets.py>`_.
For a general reference for serializers and viewsets, check `DRF documentation
<http://www.django-rest-framework.org/api-guide/viewsets/>`_.


.. _define-remote:

Define your plugin Remote
-------------------------

To define a new remote, e.g. ``ExampleRemote``:

* :class:`pulpcore.plugin.models.Remote` should be subclassed and extended with additional
  attributes to the plugin needs,
* define ``TYPE`` class attribute which is used for filtering purposes,
* create a serializer for your new remote as a subclass of
  :class:`pulpcore.plugin.serializers.RemoteSerializer`,
* create a viewset for your new remote as a subclass of
  :class:`pulpcore.plugin.viewsets.RemoteViewSet`.

:class:`~pulpcore.plugin.models.Remote` model should not be used directly anywhere in plugin code.
Only plugin-defined Remote classes are expected to be used.


There are several important aspects relevant to remote implementation which were briefly mentioned
in the :ref:`understanding-models` section:

* due to deduplication of :class:`~pulpcore.plugin.models.Content` and
  :class:`~pulpcore.plugin.models.Artifact` data, they may already exist and the remote needs to
  fetch and use them when they do.
* :class:`~pulpcore.plugin.models.ContentArtifact` associates
  :class:`~pulpcore.plugin.models.Content` and :class:`~pulpcore.plugin.models.Artifact`. If
  :class:`~pulpcore.plugin.models.Artifact` is not downloaded yet,
  :class:`~pulpcore.plugin.models.ContentArtifact` contains ``NULL`` value for
  :attr:`~pulpcore.plugin.models.ContentArtifact.artifact`. It should be updated whenever
  corresponding :class:`~pulpcore.plugin.models.Artifact` is downloaded.

The remote implementation suggestion above allows plugin writer to have an understanding and
control at a low level.

.. _define-publisher:

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

Check ``pulp_file`` implementation of `the FilePublisher
<https://github.com/pulp/pulp_file/blob/master/pulp_file/app/models.py>`_.



Define your Tasks
-----------------

Tasks such as sync and publish are needed to tell Pulp how to perform certain actions.

Sync
^^^^

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

Publish
^^^^^^^


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
