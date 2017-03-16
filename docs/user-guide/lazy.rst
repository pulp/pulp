Lazy Content Loading
====================

Pulp supports the ability to create and manipulate repositories without downloading the content.
Instead, any associated metadata for the repository is synced and published, but the retrieval of
a content unit itself is deferred until a client requests the content unit. 

.. note::

    Not all content types have repository metadata and therefore lazy content loading is not
    possible for all content types.

Lazy content loading is achieved through an optional set of services. These services can run on a
dedicated host or on a host that is also running Pulp.


Overview of Lazy Content Loading Components
-------------------------------------------
The diagram below provides a high-level overview of how the lazy content loading services interact
with the Pulp core services.

.. image:: images/lazy_component.png

Lazy content loading relies on three services:

* ``httpd`` - The Apache webserver acts as a TLS termination point and reverse proxy. This service
  handles the incoming client requests and forwards them to Squid.

* ``squid`` - The Squid process caches content and de-duplicates client requests so that the content
  is only downloaded a single time.

* ``pulp_streamer`` - The pulp-streamer process interacts with Pulp's core services to determine
  where the content is located and how to download it. It streams the content back to the client
  through Squid and Apache as it is downloaded.

Clients request the content unit from Pulp's core services. Initially, these units have not been
downloaded so Pulp redirects the client to the lazy content loading services. Once the content has
been downloaded by these services, Pulp is informed that a new content unit has been downloaded and
cached by Squid. Pulp fetches the cached unit and saves it so that when a client next requests it,
Pulp can serve it directly.


Installation
------------
The lazy content loading services can be installed using the ``pulp-lazy`` package group::

 $ sudo yum groupinstall pulp-lazy


Ensure that ``httpd``, ``squid``, and ``pulp_streamer`` are enabled to start at boot.
For Upstart-based systems::

 $ sudo chkconfig httpd on
 $ sudo chkconfig squid on
 $ sudo chkconfig pulp_streamer on

For systemd based systems::

 $ sudo systemctl enable httpd squid pulp_streamer


Configuration
-------------
Lazy content loading requires some additional configuration beyond the standard
Pulp configuration.

Pulp
^^^^
A section of the Pulp server configuration file is devoted to lazy content
loading. The configuration file contains in-line documentation for each setting.

.. note::

  By default, the lazy services are disabled.


Apache
^^^^^^
Apache must be configured to forward incoming requests to the Squid cache. Two location
directives should to be added. The first needs to appear in the VirtualHost that handles
HTTP traffic::

  Alias /streamer /var/www/streamer
  <VirtualHost *:80>
      # Any additional VirtualHost configuration goes here

      <Location /streamer/>
          DirectoryIndex disabled
          # TODO: This almost certainly isn't needed since neither squid nor pulp_streamer
          # should ever result in a redirect to the client. Need a second opinion to make
          # sure I'm not forgetting anything.
          # ProxyPassReverse http://127.0.0.1:3128/
      </Location>
      <Directory /var/www/streamer>
          WSGIAccessScript /srv/pulp/streamer_auth.wsgi
          RewriteEngine on
          # Remove the 'policy' query parameter if it is present in the request
          RewriteCond %{QUERY_STRING} (.*)(^|&|;)policy(=|%3D)([^(;|&)]+)(.*)$
          RewriteRule (.*) $1?%1%5

          # Remove the 'signature' query parameter if it is present in the request
          RewriteCond %{QUERY_STRING} (.*)(^|&|;)signature(=|%3D)([^(;|&)]+)(.*)$
          RewriteRule (.*) $1?%1%5

          RewriteRule (.*) http://127.0.0.1:3128/$1 [P]
    </Directory>
  </VirtualHost>


.. note::

  The `/var/www/streamer/` directory must exist and be owned by Apache.

The second should appear in the VirtualHost that handles HTTPS traffic. Usually this
host is already defined in ssl.conf::

  Alias /streamer /var/www/streamer
  <VirtualHost _default_:443>
    SSLEngine on

    # Additional SSL configuration should be defined here

    <Location /streamer/>
      DirectoryIndex disabled
      # TODO: This almost certainly isn't needed since neither squid nor pulp_streamer
      # should ever result in a redirect to the client. Need a second opinion to make
      # sure I'm not forgetting anything.
      # ProxyPassReverse http://127.0.0.1:3128/
    </Location>
    <Directory /var/www/streamer>
      WSGIAccessScript /srv/pulp/streamer_auth.wsgi
      RewriteEngine on
      # Remove the 'policy' query parameter if it is present in the request
      RewriteCond %{QUERY_STRING} (.*)(^|&|;)policy(=|%3D)([^(;|&)]+)(.*)$
      RewriteRule (.*) $1?%1%5

      # Remove the 'signature' query parameter if it is present in the request
      RewriteCond %{QUERY_STRING} (.*)(^|&|;)signature(=|%3D)([^(;|&)]+)(.*)$
      RewriteRule (.*) $1?%1%5

      RewriteRule (.*) http://127.0.0.1:3128/$1 [P]
    </Directory>
  </VirtualHost>


Squid
^^^^^
Squid requires some additional configuration to determine where to cache objects on
disk and how much space to use. The following Squid configuration is a good place to
begin::

  # Recommended minimum configuration:

  # Listen on port 3128 in Accelerator (caching) mode.
  http_port 3128 accel

  # Only accept connections from the local host. If the Apache reverse
  # proxy is running on a different host, adjust this accordingly.
  http_access allow localhost

  # Allow requests with a destination that matches the port squid
  # listens on, and deny everything else. This is okay because we
  # only handle requests from the Apache reverse proxy.
  acl Safe_ports port 3128
  http_access deny !Safe_ports

  # Only allow cachemgr access from localhost
  http_access allow localhost manager
  http_access deny manager

  # We strongly recommend the following be uncommented to protect innocent
  # web applications running on the proxy server who think the only
  # one who can access services on "localhost" is a local user
  http_access deny to_localhost

  # And finally deny all other access to this proxy
  http_access deny all


  # Forward requests to the Pulp Streamer. Note that the port configured here
  # must match the port the Pulp Streamer is listening on. The format for
  # entries is: cache_peer hostname type http-port icp-port [options]
  #
  # The following options are set:
  #  * no-digest: Disable request of cache digests, as the Pulp Streamer does not
  #               provide one
  #  * no-query: Disable ICP queries to the Pulp Streamer.
  #  * originserver: Causes the Pulp Streamer to be contacted as the origin server.
  #  * name: Unique name for the peer. Used to reference the peer in other directives.
  cache_peer localhost parent 8751 0 no-digest no-query originserver name=PulpStreamer

  # Allow all queries to be forwarded to the Pulp Streamer.
  cache_peer_access PulpStreamer allow all

  # Ensure all requests are allowed to be cached.
  cache allow all

  # Set the debugging level. The format is 'section,level'.
  # Valid levels are 1 to 9, with 9 being the most verbose.
  debug_options ALL,1


  # Set the minimum object size to 0 kB so all content is cached.
  minimum_object_size 0 kB

  # Set the maximum object size that can be cached. Default is to support DVD-sized
  # objects so that ISOs are cached.
  maximum_object_size 5 GB

  # Objects larger than this size will not be kept in the memory cache. This should
  # be set low enough to avoid large objects taking up all the memory cache, but
  # high enough to avoid repeatedly reading hot objects from disk.
  maximum_object_size_in_memory 100 MB

  # Set the location and size of the disk cache. Format is:
  # cache_dir type Directory-Name Fs-specific-data [options]
  #
  # * type specifies the type of storage system to use.
  # * Directory-Name is the top-level directory where cache swap files will be stored.
  #   Squid will not create this directory so it must exist and be writable by the
  #   Squid process.
  # * Fs-specific-data varies by storage system type. For 'ufs' the data is in the
  #   format: Mbytes L1 L2.
  #     - Mbytes is the number of megabytes to use in this cache directory. Note that
  #       that this should never exceed 80% of the storage space in that directory.
  #     - L1 is the number of first-level subdirectories which are created under the
  #       root cache directory (Directory-Name).
  #     - L2 is the number of second-level subdirectories which will be created under
  #       each L1 subdirectory.
  #
  # Be aware that this directive must NOT precede the 'workers' configuration option
  # and should use configuration macros or conditionals to give each squid worker that
  # requires a disk cache a dedicated cache directory.
  #
  cache_dir ufs /var/spool/squid 10000 16 256

  # Leave coredumps in the first cache dir
  coredump_dir /var/spool/squid

  #
  # Define how long objects without a explicit expiry time are considered fresh.
  # All responses from the Pulp Streamer should include a max-age and s-maxage in
  # the Cache-Control header, but this is a way to ensure all objects become
  # stale eventually.
  #
  # Add any of your own refresh_pattern entries above these.
  #
  refresh_pattern ^ftp:		1440	20%	10080
  refresh_pattern ^gopher:	1440	0%	1440
  refresh_pattern -i (/cgi-bin/|\?) 0	0%	0
  refresh_pattern .		0	20%	4320


Once all the services have been configured, start them. For Upstart-based systems::

 $ sudo service httpd start
 $ sudo service squid start
 $ sudo service pulp_streamer start

For systemd based systems::

 $ sudo systemctl start httpd squid pulp_streamer


API Usage
---------
how to enable a repo for 'lazy active' or 'lazy passive' using the importer config attribute named 
'lazy_sync'.


Pulp-admin Usage
----------------
How to configure a repo to use lazy sync, along with a recipe or example.

