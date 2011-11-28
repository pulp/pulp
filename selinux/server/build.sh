#!/bin/sh

NAME="pulp-server"
SELINUX_VARIANTS="mls strict targeted"

for selinuxvariant in ${SELINUX_VARIANTS}
do
    make NAME=${selinuxvariant} -f /usr/share/selinux/devel/Makefile
    mv ${NAME}.pp ${NAME}.pp.${selinuxvariant}
    make NAME=${selinuxvariant} -f /usr/share/selinux/devel/Makefile clean
done
