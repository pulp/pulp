#!/bin/sh

NAME="pulp-server"
MODULE_TYPE="apps"
SELINUX_VARIANTS="targeted"
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
