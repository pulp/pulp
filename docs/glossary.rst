Glossary
========

.. glossary::

    :class:`~pulpcore.plugin.models.Artifact`
        A file that belongs to a :term:`content unit<content>`.

    :class:`~pulpcore.plugin.models.Content`
        The smallest that of data that is managed by Pulp. When singular, "content unit" should be
        used. Content is added and removed to :term:`Repositories<repository>`, and can have multiple
        :term:`artifacts<artifact>`. Each content unit has a :term:`type` (like .rpm or .deb) which
        that is defined by a :term:`plugin`

    content app
        A `Django <https://docs.djangoproject.com>`_ app provided by :term:`pulpcore` that serves
        :term:`content`.

    :class:`~pulpcore.plugin.models.Distribution`
        User facing settings that specify how and where associated
        :term:`publications<publication>` are served.

    plugin
        A `Django <https://docs.djangoproject.com>`_ app that exends :term:`pulpcore` to manage one or more
        :term:`types<type>` of :term:`content`.

    publication
        The metadata and :term:`artifacts<Artifact>` of the :term:`content units<content>` in a
        :term:`repository version<RepositoryVersion>`. Publications are served by the
        :term:`content app` when they are assigned to a :term:`distribution`.

    publisher
        A :term:`plugin` defined object that contains settings required to publish a specific :term:`type` of
        :term:`content unit<content>`.

    pulpcore
        A generalized backend with a :doc:`plugins/plugin-api/overview` and a :doc:`REST
        API<integration-guide/rest-api/index>`. It uses :term:`plugins<plugin>` to manage
        :term:`content`.

    PUP
        Stands for "Pulp Update Proposal", and are the documents that specify process changes for
        the Pulp project and community.

    :class:`~pulpcore.plugin.models.Remote`
        User facing settings that specify how Pulp should interact with an external :term:`content`
        source.

    :class:`~pulpcore.app.models.Repository`
        A versioned set of :term:`content units<content>`.

    :class:`~pulpcore.app.models.RepositoryVersion`
        An immutable snapshot of the set of :term:`content units<content>` that are in a :term:`repository`.

    sync
        A :term:`plugin` defined task that fetches :term:`content` from an external source using a
        :term:`remote`. The task adds and/or removes the :term:`content units<content>` to a
        :term:`repository`, creating a new :term:`repository version<RepositoryVersion>`.

    type
        Each :term:`content unit<content>` has a type (ex. rpm or docker) which is defined by a
        :term:`Plugin<plugin>`.
