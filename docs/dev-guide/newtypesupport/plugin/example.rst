:orphan:

Plugin Example
==============

This example will cover the structure of a plugin, covering the type definition, importer, and
distributor.

In a real importer implementation, the details of how the contents of an external repository are
retrieved and how the files are downloaded are non-trivial. Similarly, the steps a distributor
will take to publish the repository will vary in complexity based on the behavior of the publish
implementation. As such, these examples will provide the basic structure of the plugins with
stubs indicating where more complex logic would occur.

.. note::
  For the purposes of this example, the code will be added to the subclasses directly. In a real
  implementation, multiple Python modules would be used for better organization.


Type Definition
---------------

Content types are defined in a JSON file. Multiple types may be defined in the same definition
file. More information on a definition's fields can be found in the :doc:`type_defs` section.

This document will use a modified version of the Puppet module type definition as an example.
This version is simplified to use only the module name as the unit key.

.. code-block:: rest

 {"types": [
     {
         "id" : "puppet_module",
         "display_name" : "Puppet Module",
         "description" : "Puppet Module",
         "unit_key" : "name",
         "search_indexes" : ["author", "tag_list"]
     }
 ]}

The type definition must be placed in the ``/usr/lib/pulp/plugins/types`` directory. The
``pulp-manage-db`` script must be run each time a definition is added or changed.


Importer
--------

Each importer must subclass the ``pulp.plugins.importer.Importer`` class. The following snippet
contains the definition of that class and its implementation of the required ``metadata()`` method.
More information on this method can be found :ref:`here <plugin_metadata>`.

.. code-block:: python

 from pulp.plugins.importer import Importer

 class PuppetModuleImporter(Importer):

     @classmethod
     def metadata(cls):
         return {
             'id' : 'puppet_importer',
             'display_name' : 'Puppet Importer',
             'types' : ['puppet_module'],
         }

.. note::
  User-visible information, such as the ``display_name`` attribute above, should be run through an
  i18n conversion method before being returned from this call.

The puppet_module content type in the ``types`` field correlates to the name of the type defined above.

The importer implementation is also required to implement the ``validate_config`` method as
:ref:`described here <plugin_config>`. Implementations will vary by importer. For this example,
a simple check to ensure a feed has been provided will be performed. If the feed is missing, the
configuration is flagged as invalid and a message to be displayed to the user is returned. If
the feed is present, the method indicates the configuration is valid (no user message is required).

.. code-block:: python

  def validate_config(self, repo, config, related_repos):
    if config.get('feed') is None:
      return False, 'Required attribute "feed" is missing'

    return True, None

At this point, other methods in ``Importer`` are subclassed depending on the desired functionality. This
example will cover the ``sync_repos`` method.

The implementation below covers a very high-level view of what a repository sync call will do. The
conduit is used to query the server for the current contents of the repository and add new units.
It is also used to update the server on the progress of the sync.

.. code-block:: python

  def sync_repo(self, repo, sync_conduit, config):

    sync_conduit.set_progress('Downloading repository metadata')
    metadata = self._fetch_repo_metadata(repo, config)
    sync_conduit.set_progress('Metadata download complete')

    new_modules = self._resolve_modules_to_download(metadata, sync_conduit)

    sync_conduit.set_progress('Downloading modules')
    self._download_and_add_modules(new_modules, sync_conduit)
    sync_conduit.set_progress('Module download and import complete')

  def _fetch_repo_metadata(repo, config):
    """
    Retrieves the listing of Puppet modules at the configured 'feed' location. The data returned from
    this call will vary based on the implementation but will likely be enough to identify each
    module in the repository.

    :return: list of module names in the external repository
    :rtype:  list
    """
    # Insert download and parse logic
    modules_in_repository = # Parse logic

    return modules_in_repository

  def _resolve_modules_to_download(metadata, sync_conduit):
    """
    Analyzes the metadata describing modules in the external repository against those already in
    the Pulp repository. The conduit is used to query the Pulp server for the repository's modules.

    Similar to _fetch_repo_metadata, the format of the returned value needs to be enough that
    the download portion of the process can fetch them.

    :return: list of module names that need to be downloaded from the external repository
    :rtype:  list
    """
    # Units currently in the repository
    module_criteria = UnitAssociationCriteria(type_ids=['puppet_module'])
    existing_modules = sync_conduit.get_units(criteria=module_criteria)

    # Calculate the difference between existing_units and what is in the metadata
    module_names_to_download = # Difference logic

    return module_names_to_download

  def _download_and_add_modules(new_modules, sync_conduit):
    """
    Performs the downloading of any missing modules and adds them to the Pulp server.
    """

    for module_name in new_modules:
      # Determine the unique identifier for the unit. This should use each of the fields for
      # the unit key as specified in the type definition.
      unit_key = {'name' : module_name}

      # Any extra information about the module is specified as its metadata. This may include
      # file size, checksum, description, etc. For this example, we'll simply leave it empty.
      metadata = {}

      # The relative path is the path and filename of the module. This must be unique across
      # all Puppet modules. Pulp will prefix this path as necessary to make it a full path
      # on the filesystem the file should reside.
      relative_path = 'modules/%s' % module_name

      # Allow Pulp to package the unit and perform any initialization it needs. This
      # initialization includes calculating the full path it will be stored at. The return
      # from this call is a pulp.plugins.Unit instance.
      pulp_unit = sync_conduit.init_unit('puppet_module', unit_key, metadata, relative_path)

      # Download the file to the Pulp-specified destination.
      # Download logic into pulp_unit.storage_path

      # If the download was successful, save the unit in Pulp's database and associate it with
      # the repository being synchronized (the conduit is scoped to the repository so it need
      # not be specified explicitly).
      sync_conduit.save_unit(pulp_unit)


Distributor
-----------

This example will loosely describe the process of exposing a Pulp repository over the local web
server.

Each distributor must subclass the ``pulp.plugins.distributor.Distributor`` class. The following snippet
contains the definition of that class and its implementation of the required ``metadata()`` method.
More information on this method can be found :ref:`here <plugin_metadata>`.

.. code-block:: python

 from pulp.plugins.distributor import Distributor

 class PuppetModuleDistributor(Distributor):

     @classmethod
     def metadata(cls):
         return {
             'id' : 'puppet_distributor',
             'display_name' : 'Puppet Distributor',
             'types' : ['puppet_module'],
         }

As with the importer, the type definition is referenced in the metadata as a supported type.

Also similar to the importer, the distributor implementation is required to implement the
``validate_config`` method as :ref:`described here <plugin_config>`. For this example,
the validation will ensure that the distributor is configured to publish over at least
HTTP or HTTPS.

.. code-block:: python

  def validate_config(self, repo, config, related_repos):
    if config.get('serve-http') is None and config.get('serve-https') is None:
      return False, 'At least one of "serve-http" or "serve-https" must be specified'

    return True, None

The ``publish_repo`` method is implemented to support the publishing operation.

The implementation below covers a very high-level view of what a repository publish call will do. The
conduit is used to query the server for the current contents of the repository and to update the server
on the progress of the sync.

.. code-block:: python

  def publish_repo(self, repo, publish_conduit, config):

    publish_conduit.set_progress('Publishing modules')
    self._publish_modules(publish_conduit, config)
    publish_conduit.set_progress('Modules published')

    publish_conduit.set_progress('Generating repository metadata')
    self._generate_metadata(publish_conduit, config)
    publish_conduit.set_progress('Metadata generation complete')

  def _publish_modules(publish_conduit, config):
    """
    For each module in the repository, creates a symlink from the location at which Pulp
    saved the module to a web-enabled directory.
    """

    criteria = UnitAssociationCriteria(type_ids=['puppet_module'])
    repo_modules = self.publish_conduit.get_units(criteria=criteria)

    # Each entry is a pulp.plugins.module.Unit instance
    for module in repo_modules:

      if config.get('serve-http') is True:
        # Create symlink from module.storage_path to HTTP-enabled directory

      if config.get('serve-https') is True:
        # Create symlink from module.storage_path to HTTPS-enabled directory

  def _generate_metadata(publish_conduit, config):
    """
    Creates the files necessary to describe the contents of the published repository. This may
    not be necessary in all distributors. In this example, we're recreating the Puppet Forge
    repository on the Pulp server, so the corresponding JSON metadata files are created.
    These files are recreated instead of simply copied from Puppet Forge as the contents
    of the repository may have changed, for instance if modules were uploaded or copied
    from another repository.
    """

    # Metadata file creation logic, using the conduit to retrieve the modules in the repository


Installation
------------

Instructions on packaging and installing plugins for production deployment
can be found at :ref:`plugin_entry_points`. For development purposes, it may be simpler to
install the plugin using the directory approach. More information can be found in the
:ref:`plugin_directory` section of this guide.


Full Example
------------

Type Definition
^^^^^^^^^^^^^^^

.. code-block:: python

 {"types": [
     {
         "id" : "puppet_module",
         "display_name" : "Puppet Module",
         "description" : "Puppet Module",
         "unit_key" : "name",
         "search_indexes" : ["author", "tag_list"]
     }
 ]}


Importer
^^^^^^^^

.. code-block:: python

 from pulp.plugins.importer import Importer

 class PuppetModuleImporter(Importer):

   @classmethod
   def metadata(cls):
       return {
           'id' : 'puppet_importer',
           'display_name' : 'Puppet Importer',
           'types' : ['puppet_module'],
       }

  def validate_config(self, repo, config, related_repos):
    if config.get('feed') is None:
      return False, 'Required attribute "feed" is missing'

    return True, None

  def sync_repo(self, repo, sync_conduit, config):

    sync_conduit.set_progress('Downloading repository metadata')
    metadata = self._fetch_repo_metadata(repo, config)
    sync_conduit.set_progress('Metadata download complete')

    new_modules = self._resolve_modules_to_download(metadata, sync_conduit)

    sync_conduit.set_progress('Downloading modules')
    self._download_and_add_modules(new_modules, sync_conduit)
    sync_conduit.set_progress('Module download and import complete')

  def _fetch_repo_metadata(repo, config):
    """
    Retrieves the listing of Puppet modules at the configured 'feed' location. The data returned from
    this call will vary based on the implementation but will likely be enough to identify each
    module in the repository.

    :return: list of module names in the external repository
    :rtype:  list
    """
    # Insert download and parse logic
    modules_in_repository = # Parse logic

    return modules_in_repository

  def _resolve_modules_to_download(metadata, sync_conduit):
    """
    Analyzes the metadata describing modules in the external repository against those already in
    the Pulp repository. The conduit is used to query the Pulp server for the repository's modules.

    Similar to _fetch_repo_metadata, the format of the returned value needs to be enough that
    the download portion of the process can fetch them.

    :return: list of module names that need to be downloaded from the external repository
    :rtype:  list
    """
    # Units currently in the repository
    module_criteria = UnitAssociationCriteria(type_ids=['puppet_module'])
    existing_modules = sync_conduit.get_units(criteria=module_criteria)

    # Calculate the difference between existing_units and what is in the metadata
    module_names_to_download = # Difference logic

    return module_names_to_download

  def _download_and_add_modules(new_modules, sync_conduit):
    """
    Performs the downloading of any missing modules and adds them to the Pulp server.
    """

    for module_name in new_modules:
      # Determine the unique identifier for the unit. This should use each of the fields for
      # the unit key as specified in the type definition.
      unit_key = {'name' : module_name}

      # Any extra information about the module is specified as its metadata. This may include
      # file size, checksum, description, etc. For this example, we'll simply leave it empty.
      metadata = {}

      # The relative path is the path and filename of the module. This must be unique across
      # all Puppet modules. Pulp will prefix this path as necessary to make it a full path
      # on the filesystem the file should reside.
      relative_path = 'modules/%s' % module_name

      # Allow Pulp to package the unit and perform any initialization it needs. This
      # initialization includes calculating the full path it will be stored at. The return
      # from this call is a pulp.plugins.Unit instance.
      pulp_unit = sync_conduit.init_unit('puppet_module', unit_key, metadata, relative_path)

      # Download the file to the Pulp-specified destination.
      # Download logic into pulp_unit.storage_path

      # If the download was successful, save the unit in Pulp's database and associate it with
      # the repository being synchronized (the conduit is scoped to the repository so it need
      # not be specified explicitly).
      sync_conduit.save_unit(pulp_unit)


Distributor
^^^^^^^^^^^

.. code-block:: python

 from pulp.plugins.distributor import Distributor

 class PuppetModuleDistributor(Distributor):

   @classmethod
   def metadata(cls):
       return {
           'id' : 'puppet_distributor',
           'display_name' : 'Puppet Distributor',
           'types' : ['puppet_module'],
       }

  def validate_config(self, repo, config, related_repos):
    if config.get('serve-http') is None and config.get('serve-https') is None:
      return False, 'At least one of "serve-http" or "serve-https" must be specified'

    return True, None

  def publish_repo(self, repo, publish_conduit, config):

    publish_conduit.set_progress('Publishing modules')
    self._publish_modules(publish_conduit, config)
    publish_conduit.set_progress('Modules published')

    publish_conduit.set_progress('Generating repository metadata')
    self._generate_metadata(publish_conduit, config)
    publish_conduit.set_progress('Metadata generation complete')

  def _publish_modules(publish_conduit, config):
    """
    For each module in the repository, creates a symlink from the location at which Pulp
    saved the module to a web-enabled directory.
    """

    criteria = UnitAssociationCriteria(type_ids=['puppet_module'])
    repo_modules = self.publish_conduit.get_units(criteria=criteria)

    # Each entry is a pulp.plugins.module.Unit instance
    for module in repo_modules:

      if config.get('serve-http') is True:
        # Create symlink from module.storage_path to HTTP-enabled directory

      if config.get('serve-https') is True:
        # Create symlink from module.storage_path to HTTPS-enabled directory

  def _generate_metadata(publish_conduit, config):
    """
    Creates the files necessary to describe the contents of the published repository. This may
    not be necessary in all distributors. In this example, we're recreating the Puppet Forge
    repository on the Pulp server, so the corresponding JSON metadata files are created.
    These files are recreated instead of simply copied from Puppet Forge as the contents
    of the repository may have changed, for instance if modules were uploaded or copied
    from another repository.
    """

    # Metadata file creation logic, using the conduit to retrieve the modules in the repository
