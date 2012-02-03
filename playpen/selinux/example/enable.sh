#!/bin/sh

NAME="example"
#SELINUX_VARIANTS="mls strict targeted"
SELINUX_VARIANTS="targeted"
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
            ${INSTALL_DIR}/selinux/${selinuxvariant}/${NAME}.pp
    done
fi

