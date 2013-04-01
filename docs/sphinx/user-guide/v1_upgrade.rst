:orphan:

Pulp v1 Upgrades
================

Pulp 2.1 and beyond support upgrading from Pulp 1.1. Some manual steps must be run to
complete the upgrade.

Server
^^^^^^

1. Stop the server:

::

  $ sudo systemctl stop httpd.service
  or
  $ sudo service httpd stop

2. Install the v2 package groups:

::

  $ sudo yum group-install pulp-server pulp-admin

3. Run the ``pulp-v1-upgrade`` script. This script upgrades the database to the new format and
   makes the appropriate filesystem changes.

4. Run the ``pulp-v1-upgrade-selinux`` script to apply the necessary policies.

5. Start the server:

::

  $ sudo systemctl start httpd.service
  or
  $ sudo service httpd start

6. (optional) After upgrade, repositories are left unpublished, meaning they are stored in
   the Pulp database but not accessible over HTTPS. The ``pulp-v1-upgrade-publish`` script
   can be used to publish all repositories. Alternatively, repositories can be later
   published individually using the admin client.

Admin Client
^^^^^^^^^^^^

1. The entries in the admin configuration have changed in v2. The v2 version of the file
   is installed as ``/etc/pulp/admin/admin.conf.rpmnew``. The existing file (``admin.conf``)
   must be replaced with this file. It is likely that the ``host`` field will need to be
   updated to point to the hostname of the Pulp server.

Consumer Client
^^^^^^^^^^^^^^^

1. The entries in the consumer configuration have changed in v2. The v2 version of the file
   is installed as ``/etc/pulp/consumer.conf.rpmnew``. The existing file (``consumer.conf``)
   must be replaced with this file. It is likely that the ``host`` field will need to be updated
   to point to the hostname of the Pulp server.

2. The client identification certificate must be moved to its new location:

::

  $ sudo mv /etc/pki/pulp/consumer/cert.pem /etc/pki/pulp/consumer/consumer-cert.pem


Pulp Agent
^^^^^^^^^^

1. On the consumer, the package owning ``/etc/init.d/pulp-admin`` changed in v2.
After upgrade, this symlink needs to be manually recreated.

::

 $ sudo ln -s /etc/init.d/goferd /etc/init.d/pulp-agent
 $ sudo chkconfig pulp-agent on
