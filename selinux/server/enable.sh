#!/bin/sh

NAME="pulp-server"
SELINUX_VARIANTS="targeted"
#This script will be called from pulp RPM and needs the ability to use the specified macro
if [ $# -lt 1 ]; then
    INSTALL_DIR=/usr/share
else
    INSTALL_DIR=$1
fi

# httpd_can_network_connect
#   bz 736788, allows repo sync through a proxy to work

# httpd_tmp_exec
#   Pulp is indirectly creating a script in /tmp and asking Apache to execute it 
#   possibly from mod_wsgi?
#   TODO: This is an area to investigate further.
#   Ideal is to remove the ability for Apache to execute temporary files

if /usr/sbin/selinuxenabled ; then
    for selinuxvariant in ${SELINUX_VARIANTS}
    do
        /usr/sbin/semanage -i - << _EOF
            module -a ${INSTALL_DIR}/selinux/${selinuxvariant}/${NAME}.pp
            boolean -m --on httpd_can_network_connect
            boolean -m --on httpd_tmp_exec
_EOF
done
semanage port -l | grep amqp_port_t | grep tcp | grep 5674 > /dev/null || \
    /usr/sbin/semanage port -a -t amqp_port_t -p tcp 5674
semanage port -l | grep amqp_port_t | grep udp | grep 5674 > /dev/null || \
    /usr/sbin/semanage port -a -t amqp_port_t -p udp 5674
fi
