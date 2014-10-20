#!/bin/sh

PACKAGE_NAMES=( "pulp-server" "pulp-celery" )
SELINUX_VARIANTS="targeted"

#This script will be called from pulp RPM and needs the ability to use the specified macro
if [ $# -lt 1 ]; then
    INSTALL_DIR=/usr/share
else
    INSTALL_DIR=$1
fi

if /usr/sbin/selinuxenabled ; then
    for NAME in ${PACKAGE_NAMES[@]}
    do
        for selinuxvariant in ${SELINUX_VARIANTS}
        do
            /usr/sbin/semodule -i ${INSTALL_DIR}/selinux/${selinuxvariant}/${NAME}.pp
        done
    done

# httpd_can_network_connect
#   bz 736788, allows repo sync through a proxy to work

# httpd_tmp_exec
#   Pulp is indirectly creating a script in /tmp and asking Apache to execute it
#   possibly from mod_wsgi?
#   TODO: This is an area to investigate further.
#   Ideal is to remove the ability for Apache to execute temporary files

# Turn on booleans
/usr/sbin/semanage -i - << _EOF
boolean -m --on httpd_can_network_connect
boolean -m --on httpd_tmp_exec
_EOF

fi
