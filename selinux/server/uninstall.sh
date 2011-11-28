#!/bin/sh

NAME="pulp-server"
SELINUX_VARIANTS="mls strict targeted"

for selinuxvariant in %{selinux_variants}
do
    /usr/sbin/semodule -s ${selinuxvariant} -r ${NAME} &> /dev/null || :
done
