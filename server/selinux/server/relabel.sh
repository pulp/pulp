#!/usr/bin/env bash

function version_less_than () {
# Determines if the version passed in as the first argument is less than the version in the second
# argument.
    [[ $(echo -e $1'\n'$2|sort -V|head -n 1) != $2 ]]
}

# Set the previous version to 0.0 if one is not passed in
if [ -z $1 ]
then
    set -- "0.0"
fi

# If upgrading from before 2.4.0
if version_less_than $1 '2.4.0'
then
    /sbin/restorecon -i -R /etc/httpd/conf.d/pulp.conf
    /sbin/restorecon -i -R /etc/pulp
    /sbin/restorecon -i -R /etc/pki/pulp
    /sbin/restorecon -i /usr/bin/pulp-admin
    /sbin/restorecon -i /usr/bin/pulp-consumer
    /sbin/restorecon -i -R /var/lib/pulp
    /sbin/restorecon -i -R /var/log/pulp
fi
# If upgrading from before 2.5.0
if version_less_than $1 '2.5.0'
then
    /sbin/restorecon -i /usr/bin/celery
fi
# If upgrading from before 2.7.0
if version_less_than $1 '2.7.0'
then
    /sbin/restorecon -i -R /var/cache/pulp
    /sbin/restorecon -i -R /var/run/pulp
fi
# If upgrading from before 2.8.0
if version_less_than $1 '2.8.0'
then
    /sbin/restorecon -i -R /usr/share/pulp/wsgi
    /sbin/restorecon -i /usr/bin/pulp_streamer
fi
