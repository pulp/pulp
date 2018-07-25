.. _stages-docs:

pulpcore.plugin.stages
======================

Plugin writers can use the Stages API to create a high-performance download-and-saving pipeline
to make writing sync code easier. There are two parts to the API:

1. DeclarativeVersion is a generic pipeline useful for most synchronization use cases.
2. The Stages themselves


.. _declarative-version:

DeclarativeVersion
^^^^^^^^^^^^^^^^^^

.. autoclass:: pulpcore.plugin.stages.DeclarativeVersion

.. autoclass:: pulpcore.plugin.stages.FirstStage

.. autoclass:: pulpcore.plugin.stages.DeclarativeArtifact

.. autoclass:: pulpcore.plugin.stages.DeclarativeContent


.. _stages-api:

Stages API
^^^^^^^^^^

.. autofunction:: pulpcore.plugin.stages.create_pipeline

.. autofunction:: pulpcore.plugin.stages.end_stage


.. _artifact-stages:

Artifact Related Stages
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: pulpcore.plugin.stages.artifact_downloader

.. autofunction:: pulpcore.plugin.stages.artifact_saver

.. autofunction:: pulpcore.plugin.stages.query_existing_artifacts


.. _content-stages:

Content Related Stages
^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: pulpcore.plugin.stages.content_unit_saver

.. autofunction:: pulpcore.plugin.stages.query_existing_content_units


.. _content-association-stages:

Content Association and Unassociation Stages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: pulpcore.plugin.stages.content_unit_association

.. autoclass:: pulpcore.plugin.stages.content_unit_unassociation
