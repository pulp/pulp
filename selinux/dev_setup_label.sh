#!/bin/bash
PULP_SRC_DIR=`readlink -f $(dirname $0)/../`

echo "Assuming Pulp git checkout is at ${PULP_SRC_DIR}"
/usr/sbin/semanage fcontext -a -t httpd_config_t "${PULP_SRC_DIR}/etc/httpd(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/etc/httpd

/usr/sbin/semanage fcontext -a -t pulp_certs_t "${PULP_SRC_DIR}/etc/pki/pulp(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/etc/pki/pulp

/usr/sbin/semanage fcontext -a -t pulp_config_t "${PULP_SRC_DIR}/etc/pulp(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/etc/pulp
