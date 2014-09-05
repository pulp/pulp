#!/bin/sh

PACKAGE_NAMES=( "pulp-server" "pulp-celery" )
SELINUX_VARIANTS="targeted"

for selinuxvariant in ${SELINUX_VARIANTS}
do
    for NAME in ${PACKAGE_NAMES[@]}
    do
        make NAME=${NAME} -f /usr/share/selinux/devel/Makefile DISTRO=$1
        if [ "$?" -ne "0" ]; then
            echo "Error building policy: ${selinuxvariant}"
            exit 1
        fi

        mv ${NAME}.pp ${NAME}.pp.${selinuxvariant}

        make NAME=${NAME} -f /usr/share/selinux/devel/Makefile clean DISTRO=$1
        if [ "$?" -ne "0" ]; then
            echo "Error cleaning policy: ${selinuxvariant}"
            exit 1
        fi
    done
done
