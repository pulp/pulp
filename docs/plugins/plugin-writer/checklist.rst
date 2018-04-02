A Plugin Completeness Checklist
===============================

 * :ref:`Plugin django app is defined using PulpAppConfig as a parent <plugin-django-application>`
 * :ref:`Plugin entry point is defined <plugin-entry-point>`
 * `pulpcore-plugin is specified as a requirement <https://github.com/pulp/pulp_file/blob/master/setup.py#L6>`_
 * Necessary models/serializers/viewsets are :ref:`defined <subclassing-platform-models>` and :ref:`discoverable <model-serializer-viewset-discovery>`. At a minimum:

   * models for plugin content type, remote, publisher
   * serializers for plugin content type, remote, publisher
   * viewset for plugin content type, remote, publisher

 * :ref:`Errors are handled according to Pulp conventions <error-handling-basics>`
 * Docs for plugin are available (any location and format preferred and provided by plugin writer)
 

