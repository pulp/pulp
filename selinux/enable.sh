#!/bin/sh

NAME="pulp"
SELINUX_VARIANTS="mls strict targeted"
#This script will be called from pulp RPM and needs the ability to use the specified macro
if [ $# -lt 1 ]; then
    INSTALL_DIR=/usr/share
else
    INSTALL_DIR=$1
fi

if /usr/sbin/selinuxenabled ; then
    for selinuxvariant in ${SELINUX_VARIANTS}
    do
        /usr/sbin/semodule -s ${selinuxvariant} -i \
            ${INSTALL_DIR}/selinux/${selinuxvariant}/${NAME}.pp &> /dev/null || :
    done
fi


/sbin/restorecon -R /etc/httpd/conf.d/pulp.conf
/sbin/restorecon -R /etc/pulp
/sbin/restorecon -R /etc/pki/content
/sbin/restorecon -R /etc/pki/pulp
/sbin/restorecon -R /etc/init.d/pulp-server
/sbin/restorecon -R /srv/pulp
/sbin/restorecon -R /usr/bin/pulp-admin
/sbin/restorecon -R /usr/bin/pulp-consumer
/sbin/restorecon -R /usr/bin/pulp-migrate
/sbin/restorecon -R /var/lib/pulp
/sbin/restorecon -R /var/log/pulp






