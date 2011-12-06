#!/bin/sh

NAME="pulp-server"
MODULE_TYPE="apps"
SELINUX_VARIANTS="mls strict targeted"
#This script will be called from pulp RPM and needs the ability to install
# into a temporary buildroot
if [ $# -lt 1 ]; then
    INSTALL_DIR=/usr/share
else
    INSTALL_DIR=$1
fi

for selinuxvariant in ${SELINUX_VARIANTS}
do
    install -d ${INSTALL_DIR}/selinux/${selinuxvariant}
    install -p -m 644 ${NAME}.pp.${selinuxvariant} \
               ${INSTALL_DIR}/selinux/${selinuxvariant}/${NAME}.pp
done
# Install SELinux interfaces
install -d ${INSTALL_DIR}/selinux/devel/include/${MODULE_TYPE}
install -p -m 644 ${NAME}.if ${INSTALL_DIR}/selinux/devel/include/${MODULE_TYPE}/${NAME}.if

# Hardlink identical policy module packages together
/usr/sbin/hardlink -cv ${INSTALL_DIR}/selinux

#bz 736788, allows repo sync through a proxy to work
/usr/sbin/setsebool -P httpd_can_network_connect 1

# Pulp is indirectly creating a script in /tmp and asking Apache to execute it 
# possibly from mod_wsgi?
# TODO: This is an area to investigate further.
# Ideal is to remove the ability for Apache to execute temporary files
/usr/sbin/setsebool -P httpd_tmp_exec 1
