#!/bin/sh

PACKAGE_NAMES=( "pulp-celery" "pulp-server" )
SELINUX_VARIANTS="targeted"
MODULE_TYPE="apps"
INSTALL_DIR="/usr/share"

for NAME in ${PACKAGE_NAMES[@]}
do
    for selinuxvariant in ${SELINUX_VARIANTS}
    do
        /usr/sbin/semodule -s ${selinuxvariant} -r ${NAME} &> /dev/null || :
        rm -f ${INSTALL_DIR}/${selinuxvariant}/${NAME}.pp
    done

    rm -f ${INSTALL_DIR}/selinux/devel/include/${MODULE_TYPE}/${NAME}.if
done