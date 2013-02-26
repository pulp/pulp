:orphan:

Pulp v1 Upgrades
================

Pulp 2.1 and beyond support upgrading from Pulp 1.1. Some manual steps must be run to
complete the upgrade.

1. Stop the server:

::

  $ systemctl stop httpd.service
  or
  $ service httpd stop

2. Install the v2 package groups:

::

  $ yum install @pulp-server @pulp-admin

3. Run the ``pulp-v1-upgrade`` script. This script upgrades the database to the new format and
   makes the appropriate filesystem changes.

4. Run the ``pulp-v1-upgrade-selinux`` script to apply the necessary policies.

5. Start the server:

::

  $ systemctl start httpd.service
  or
  $ service httpd start

6. (optional) After upgrade, repositories are left unpublished, meaning they are stored in
   the Pulp database but not accessible over HTTPS. The ``pulp-v1-upgrade-publish`` script
   can be used to publish all repositories. Alternatively, repositories can be later
   published individually using the admin client.

