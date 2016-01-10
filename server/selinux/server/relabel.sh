#!/usr/bin/env bash

# If upgrading from before 2.4.0
if [[ $1 < '2.4.0' ]]
then
    /sbin/restorecon -i -R /etc/httpd/conf.d/pulp.conf
    /sbin/restorecon -i -R /etc/pulp
    /sbin/restorecon -i -R /etc/pki/pulp
    /sbin/restorecon -i -R /srv/pulp
    /sbin/restorecon -i -R /usr/bin/pulp-admin
    /sbin/restorecon -i -R /usr/bin/pulp-consumer
    /sbin/restorecon -i -R /var/lib/pulp
    /sbin/restorecon -i -R /var/log/pulp
fi
# If upgrading from before 2.5.0
if [[ $1 < '2.5.0' ]]
then
    # Relabel the celery binary
    /sbin/restorecon -i -R /usr/bin/celery
fi
# If upgrading from before 2.7.0
if [[ $1 < '2.7.0' ]]
then
    /sbin/restorecon -i -R /var/cache/pulp
    /sbin/restorecon -i -R /var/run/pulp
fi
