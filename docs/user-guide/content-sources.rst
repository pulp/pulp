Content Sources
===============

Pulp supports a generic concept of *Alternate Content Sources* that is independent of Importers
and Repositories. Each content source is a potential alternate provider of files that are
associated with content units in Pulp. Pulp maintains a catalog of the content provided by
each source which is periodically refreshed using a *Cataloger* server-side plugin. During a refresh,
the cataloger queries the content source using this information to update the catalog. The
next time Pulp needs to download a file associated with a content unit, it searches the catalog
for alternate sources based on the source's *priority*. Each alternate source is tried in *priority*
order. If the file cannot be successfully downloaded from one of the alternate sources, it is
finally downloaded from the original (primary) source.


Defining A Content Source
^^^^^^^^^^^^^^^^^^^^^^^^^

Content sources are defined in ``/etc/pulp/content/sources/conf.d``. Each file with a .conf suffix
may contain one or more sections. Each section defines a content source.

The [section] defines the content source ID. The following properties
are supported:

 - **enabled** <bool>
     The content source is enabled. Disabled sources are ignored.
 - **name** <str>
     The content source display name.
 - **type** <str>
     The type of content source. Must correspond to the ID of a cataloger plugin ID.
 - **priority** <int>
     The *optional* source priority used when downloading content. (0 is highest and the default).
 - **expires** <str>
     How long until cataloged information expires. The default unit is seconds but
     and optional suffix can (and should) be used. Supported suffixes:
     (s=seconds, m=minutes, h=hours, d=days)
 - **base_url** <str>
     The URL used to fetch info used to refresh the catalog.
 - **paths** <str>
     An *optional* list of URL relative paths. Delimited by space or newline.
 - **max_concurrent** <int>
     Limit the number of concurrent downloads.
 - **max_speed** <int>
     Limit the bandwidth used during downloads.
 - **ssl_ca_cert** <str>
     An optional SSL CA certificate (absolute path).
 - **ssl_validation** <bool>
     An optional flag to validate the server SSL certificate using the CA.
 - **ssl_client_cert** <str>
     An optional SSL client certificate (absolute path).
 - **ssl_client_key** <str>
     An optional SSL client key (absolute path).
 - **proxy_url** <str>
     An optional URL for a proxy.
 - **proxy_port** <short>
     An optional proxy port#.
 - **proxy_username** <str>
     An optional proxy userid.
 - **proxy_password** <str>
     An optional proxy password.

Example:
 
::

 [content-world]
 enabled: 1
 priority: 0
 expires: 3d
 name: Content World
 type: yum
 base_url: http://content-world/content/
 url: f18/x86_64/os/ \
      f18/i386/os/ \
      f19/x86_64/os \
      f19/i386/os
 max_concurrent: 10
 max_speed: 1000
 ssl_ca_cert: /etc/pki/tls/certs/content-world.ca
 ssl_client_key: /etc/pki/tls/private/content-world.key
 ssl_client_cert: /etc/pki/tls/certs/content-world.crt


Recipes
^^^^^^^

The pulp-admin client can be use to list all defined content sources as follows::

  $ pulp-admin content sources list

  +----------------------------------------------------------------------+
                              Content Sources
  +----------------------------------------------------------------------+

  Base URL:       http://content-world/content/
  Enabled:        1
  Expires:        3d
  Max Concurrent: 2
  Name:           Content World
  Paths:          f18/x86_64/os/ f18/i386/os/ f19/x86_64/os f19/i386/os
  Priority:       0
  Source Id:      content-world
  SSL Validation: true
  Type:           yum

The pulp-admin client can be used to delete entries contributed by specific content
sources as follows::

  $ pulp-admin content catalog delete -s content-world
  Successfully deleted [10] catalog entries.



