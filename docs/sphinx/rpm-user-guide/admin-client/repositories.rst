Repositories
============

.. _repo-create:

Create
------
New repositories are created through the ``repo create`` command.

The following options are available to the create repository command. The ID
and feed options are required; all others are optional.

Basic
^^^^^

``--id``
  Unique identifier for the repository. Valid characters include letters,
  numbers, hyphen (``-``) and underscore (``_``). The ID is case sensitive;
  "pulp" and "Pulp" are two separate repositories. An ID is required at repository
  creation time.

``--display_name``
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

Publishing
^^^^^^^^^^

``--relative_url``
  Relative path at which the repository will be served. If this is not specified,
  the relative path is derived from the ``feed`` option.

``--serve_http``
  Flag indicating if the repository will be served over a non-SSL connection.
  Valid values to this option are ``true`` and ``false``.

``--serve_https``
  Flag indicating if the repository will be served over an SSL connection. If
  this is set to true, the ``host_ca`` option should also be specified to ensure
  consumers bound to this repository have the necessary certificate to validate
  the SSL connection. Valid values to this option are ``true`` and ``false``.

``--checksum_type``
  Specifies the type of checksum to use during metadata generation.

``--gpg_key``
  GPG key used to sign RPMs in this repository. This key will be made available
  to consumers to use in verifying content in the repository. The value to this
  option must be the full path to the GPG key file to upload to the server.

Feed Authentication
^^^^^^^^^^^^^^^^^^^

``--feed_ca_cert``
  CA certificate used to validate the feed source's SSL certificate (for feeds
  exposed over HTTPS). This option is ignored if ``verify_feed_ssl`` is false.

``--verify_feed_ssl``
  Indicates if the server's SSL certificate is verified against the CA certificate
  uploaded using ``feed_ca_cert``. Has no effect for non-SSL feeds. Valid values
  to this option are ``true`` and ``false``.

``--feed_cert``
  Certificate used as the client certificate when synchronizing the repository.
  This is used to communicate authentication information to the feed source.
  The value to this option must be the full path to the certificate to upload.
  The specified file may be the certificate itself or a single file containing
  both the certificate and private key.

``--feed_key``
  Private key to the certificate specified in ``feed_cert``, assuming it is not
  included in the certificate file itself.

Client Authentication
^^^^^^^^^^^^^^^^^^^^^

``--host_ca``
  CA certificate used to sign the SSL certificate the server is using to host
  this repository. This certificate will be made available to bound consumers so
  they can verify the server's identity. The value to this option must be the
  full path to the certificate.

``--auth_ca``
  CA certificate that was used to sign the certificate specified in ``auth_cert``.
  The server will use this CA to verify that the incoming request's client certificate
  is signed by the correct source and is not forged. The value to this option
  must be the full path to the CA certificate file to upload.

``--auth_cert``
  Certificate that will be provided to consumers bound to this repository. This
  certificate should contain entitlement information to grant access to this
  repository, assuming the repository is protected. The value to this option must
  be the full path to the certificate file to upload. The file must contain both
  the certificate itself and its private key.

Proxy
^^^^^

``--proxy_url``
  Indicates the URL to use as a proxy server when synchronizing this repository.

``--proxy_port``
  Port to connect to on the proxy server.

``--proxy_user``
  Username to pass to the proxy server if it requires authentication.

``--proxy_pass``
  Password to use for proxy server authentication.

Content Verification
^^^^^^^^^^^^^^^^^^^^

``--verify_size``
  If true, as the repository is synchronized the size of each file will be verified
  against the metadata's expectation. Valid values to this option are ``true``
  and ``false``.

``--verify_checksum``
  If true, as the repository is synchronized the checksum of each file will be
  verified against the metadata's expectation. Valid values to this option are
  ``true`` and ``false``.

Update
------

Configuration for a repository is updated using the ``repo update`` command.
All values may be updated except for the repository's ID. Configuration values
can be removed (and thus reset to the default) by omitting a value or specifying
``""`` as the value. For example::

 repo update --id demo --verify_checksum "" --proxy_url=

See the documentation for :ref:`repository create <repo-create>` for more
information on the possible configuration.

Delete
------

List
----

Unit Search
-----------

Synchronize
-----------

Sync Schedules
--------------

