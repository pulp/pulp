Repository Lifecycle
====================

.. _repo-create:

Create a New Repository
-----------------------

New repositories are created through the ``repo create`` command.

The following options are available to the create repository command. All
arguments, with the exception of ID, are optional. In the event a repository
does not have a feed, the relative path is also required. If a feed is specified,
the relative path will be derived from it unless otherwise overridden.

Basic
^^^^^

``--repo-id``
  Unique identifier for the repository. Valid characters include letters,
  numbers, hyphen (``-``) and underscore (``_``). The ID is case sensitive;
  "pulp" and "Pulp" are two separate repositories. An ID is required at repository
  creation time.

``--display-name``
  User-friendly name for the repository.

``--description``
  Arbitrary, user-friendly text used to indicate the usage and content of the
  repository.

``--note``
  Adds a single key-value pair to the repository's metadata. Multiple pairs can
  be specified by specifying this option more than once. The value of this option
  must be specified as the key and its value separated by an equal sign. Example
  usage: ``--note k1=v1 --note k2=v2``.

``--feed``
  URL where the repository's content will be synchronized from. This can be either
  an HTTP URL or a location on disk represented as a file URL.

Synchronization
^^^^^^^^^^^^^^^

``--only-newest``
  Flag indicating if only the newest version of each package should be downloaded
  during synchronization.

``--skip-types``
  Comma-separated list of types to omit when synchronizing from the source. If
  unspecified, all types will be synchronized. Valid values are: packages,
  distributions, errata. Example usage to only synchronize packages:
  ``--skip-types distributions,errata``

``--verify-size``
  If true, as the repository is synchronized the size of each file will be verified
  against the metadata's expectation. Valid values to this option are ``true``
  and ``false``.

``--verify-checksum``
  If true, as the repository is synchronized the checksum of each file will be
  verified against the metadata's expectation. Valid values to this option are
  ``true`` and ``false``.

``--remove-old``
  If true, as the repository is synchronized old rpms will be removed. Valid values 
  to this option are ``true`` and ``false``.

``--retain-old-count``
  Count indicating how many old rpm versions to retain; defaults to 0. This count
  only takes effect when ``--remove-old`` option is set to ``true``.

Publishing
^^^^^^^^^^

``--relative-url``
  Relative path at which the repository will be served. If this is not specified,
  the relative path is derived from the ``feed`` option.

``--serve-http``
  Flag indicating if the repository will be served over a non-SSL connection.
  Valid values to this option are ``true`` and ``false``.

``--serve-https``
  Flag indicating if the repository will be served over an SSL connection. If
  this is set to true, the ``host-ca`` option should also be specified to ensure
  consumers bound to this repository have the necessary certificate to validate
  the SSL connection. Valid values to this option are ``true`` and ``false``.

``--checksum-type``
  Specifies the type of checksum to use during metadata generation.

``--gpg-key``
  GPG key used to sign RPMs in this repository. This key will be made available
  to consumers to use in verifying content in the repository. The value to this
  option must be the full path to the GPG key file to upload to the server.

``--regenerate-metadata``
  Flag indicating the repository metadata should be regenerated rather than
  reused from the external source.

Feed Authentication
^^^^^^^^^^^^^^^^^^^

``--feed-ca-cert``
  CA certificate used to validate the feed source's SSL certificate (for feeds
  exposed over HTTPS). This option is ignored if ``verify_feed_ssl`` is false.

``--verify-feed-ssl``
  Indicates if the server's SSL certificate is verified against the CA certificate
  uploaded using ``feed-ca-cert``. Has no effect for non-SSL feeds. Valid values
  to this option are ``true`` and ``false``.

``--feed-cert``
  Certificate used as the client certificate when synchronizing the repository.
  This is used to communicate authentication information to the feed source.
  The value to this option must be the full path to the certificate to upload.
  The specified file may be the certificate itself or a single file containing
  both the certificate and private key.

``--feed-key``
  Private key to the certificate specified in ``feed-cert``, assuming it is not
  included in the certificate file itself.

Client Authentication
^^^^^^^^^^^^^^^^^^^^^

``--host-ca``
  CA certificate used to sign the SSL certificate the server is using to host
  this repository. This certificate will be made available to bound consumers so
  they can verify the server's identity. The value to this option must be the
  full path to the certificate.

``--auth-ca``
  CA certificate that was used to sign the certificate specified in ``auth-cert``.
  The server will use this CA to verify that the incoming request's client certificate
  is signed by the correct source and is not forged. The value to this option
  must be the full path to the CA certificate file to upload.

``--auth-cert``
  Certificate that will be provided to consumers bound to this repository. This
  certificate should contain entitlement information to grant access to this
  repository, assuming the repository is protected. The value to this option must
  be the full path to the certificate file to upload. The file must contain both
  the certificate itself and its private key.

Proxy
^^^^^

``--proxy-url``
  Indicates the URL to use as a proxy server when synchronizing this repository.

``--proxy-port``
  Port to connect to on the proxy server.

``--proxy-user``
  Username to pass to the proxy server if it requires authentication.

``--proxy-pass``
  Password to use for proxy server authentication.

Throttling
^^^^^^^^^^

``--max-speed``
  Maximum bandwidth used per download thread in KB/sec.

``--num-threads``
  Number of threads used when synchronizing the repository. This count controls
  the download threads themselves and has no bearing on the number of operations
  the Pulp server can execute at a given time.

.. _repo-update:

Update an Existing Repository
-----------------------------

Configuration for a repository is updated using the ``repo update`` command.
All values may be updated except for the repository's ID. Configuration values
can be removed (and thus reset to the default) by omitting a value or specifying
``""`` as the value. For example::

 $ repo update --repo-id demo --verify-checksum "" --proxy-url=

See the documentation for :ref:`repository create <repo-create>` for more
information on the possible configuration.

Delete a Repository
-------------------

Repositories are deleted using the ``repo delete`` command. The only argument
to this call is the ID of the repository to delete and is required.

Deleting a repository removes the repository and its association to any packages
from the Pulp server. The published repository, served over HTTP and/or HTTPS,
is also deleted.

The individual packages themselves are not deleted from the Pulp server. The
documentation for that process can be found under the
:ref:`Orphaned Packages <orphaned-packages>` section.

List All Repositories
---------------------

The ``repo list`` command displays a list of all repositories in the Pulp server.
By default, only a summary view of the repository is displayed, including ID,
name, description, notes, and number of units in the repository.

Notably missing from the summary view is the full configuration for the
repository. This can be displayed by passing the ``--details`` flag to the
list command.

Summary view example::

 $ pulp-admin repo list
 +----------------------------------------------------------------------+
                               Repositories
 +----------------------------------------------------------------------+

 Id:                 ks
 Display Name:       ks
 Description:        None
 Content Unit Count: 56
 Notes:

 Id:                 pulp-rhel6-i386
 Display Name:       Pulp RHEL 6 i386
 Description:        None
 Content Unit Count: 18
 Notes:

Details view example::

 $ pulp-admin repo list --details
 +----------------------------------------------------------------------+
                               Repositories
 +----------------------------------------------------------------------+

 Id:                 ks
 Display Name:       ks
 Description:        None
 Content Unit Count: 56
 Notes:
 Sync Config:
   Feed: http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/
 Publish Config:
   Generate Metadata: True
   Http:              False
   Https:             True
   Relative URL:      /repos/pulp/pulp/demo_repos/pulp_unittest/

 Id:                 pulp-rhel6-i386
 Display Name:       Pulp RHEL 6 i386
 Description:        None
 Content Unit Count: 18
 Notes:
 Sync Config:
   Feed: http://repos.fedorapeople.org/repos/pulp/pulp/dev/stable/6Server/i386/
 Publish Config:
   Generate Metadata: True
   Http:              True
   Https:             False
   Relative URL:      /repos/pulp/pulp/dev/stable/6Server/i386/
