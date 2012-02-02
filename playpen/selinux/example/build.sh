#!/bin/sh

NAME="example"
SELINUX_VARIANTS="mls strict targeted"

for selinuxvariant in ${SELINUX_VARIANTS}
do
    make NAME=${selinuxvariant} -f /usr/share/selinux/devel/Makefile
    if [ "$?" -ne "0" ]; then
        echo "Error building policy: ${selinuxvariant}"
        exit 1
    fi
    mv ${NAME}.pp ${NAME}.pp.${selinuxvariant}
    make NAME=${selinuxvariant} -f /usr/share/selinux/devel/Makefile clean
    if [ "$?" -ne "0" ]; then
        echo "Error cleaning policy: ${selinuxvariant}"
        exit 1
    fi
done
