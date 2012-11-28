#!/bin/sh

/sbin/restorecon -R /etc/httpd/conf.d/pulp.conf
/sbin/restorecon -R /etc/pulp
/sbin/restorecon -R /etc/pki/pulp
/sbin/restorecon -R /srv/pulp
/sbin/restorecon -R /usr/bin/pulp-admin
/sbin/restorecon -R /usr/bin/pulp-consumer
/sbin/restorecon -R /var/lib/pulp
/sbin/restorecon -R /var/log/pulp








