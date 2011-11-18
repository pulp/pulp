#!/bin/bash
PULP_SRC_DIR=`readlink -f $(dirname $0)/../`
# We will check the python site-packages dir for developmental installs of Grinder & Gofer
PYTHON_SITE_PKGS="/usr/lib/python"`python -c 'import sys; print sys.version[0:3]'`"/site-packages"

echo "Assuming Pulp git checkout is at ${PULP_SRC_DIR}"
/usr/sbin/semanage fcontext -a -t httpd_config_t "${PULP_SRC_DIR}/etc/httpd(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/etc/httpd

/usr/sbin/semanage fcontext -a -t pulp_certs_t "${PULP_SRC_DIR}/etc/pki/pulp(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/etc/pki/pulp

/usr/sbin/semanage fcontext -a -t pulp_config_t "${PULP_SRC_DIR}/etc/pulp(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/etc/pulp

/usr/sbin/semanage fcontext -a -t pulp_exec_t "${PULP_SRC_DIR}/srv/pulp(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/srv/pulp

/usr/sbin/semanage fcontext -a -t lib_t "${PULP_SRC_DIR}/src(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/src

if [ -e ${PYTHON_SITE_PKGS}/gofer.egg-link ]; then
    GOFER_SRC=`head -n 1 ${PYTHON_SITE_PKGS}/gofer.egg-link`
    if [ -d ${GOFER_SRC} ]; then
        echo "Updating fcontext on ${GOFER_SRC}"
        /usr/sbin/semanage fcontext -a -t lib_t "${GOFER_SRC}(/.*)?"
        /sbin/restorecon -R ${GOFER_SRC}
    fi
fi

if [ -e ${PYTHON_SITE_PKGS}/grinder.egg-link ]; then
    GRINDER_SRC=`head -n 1 ${PYTHON_SITE_PKGS}/grinder.egg-link`
    if [ -d ${GRINDER_SRC} ]; then
        echo "Updating fcontext on ${GRINDER_SRC}"
        /usr/sbin/semanage fcontext -a -t lib_t "${GRINDER_SRC}(/.*)?"
        /sbin/restorecon -R ${GRINDER_SRC}
    fi
fi
