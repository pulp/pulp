#!/bin/sh

/sbin/restorecon -i -R /etc/httpd/conf.d/pulp.conf
/sbin/restorecon -i -R /etc/pulp
/sbin/restorecon -i -R /etc/pki/pulp
/sbin/restorecon -i -R /srv/pulp
/sbin/restorecon -i -R /usr/bin/pulp-admin
/sbin/restorecon -i -R /usr/bin/pulp-consumer
/sbin/restorecon -i -R /var/lib/pulp
/sbin/restorecon -i -R /var/log/pulp
/sbin/restorecon -i -R /var/www/pulp_puppet







