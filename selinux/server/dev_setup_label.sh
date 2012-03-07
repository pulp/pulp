#!/bin/bash
PULP_SRC_DIR=`readlink -f $(dirname $0)/../../`
# We will check the python site-packages dir for developmental installs of Grinder & Gofer
PYTHON_SITE_PKGS="/usr/lib/python"`python -c 'import sys; print sys.version[0:3]'`"/site-packages"

MODE="install"
if [ $# -ne 0 ] ; then
    if [[ $1 = "clean" ]] ; then
        MODE="clean"
        echo "Running in clean mode"
    else
        echo "Unknown mode: $1"
        echo "If you want to cleanup/remove previously set context rules run as: '$0 clean'"
        exit
    fi
fi

function adjust_context()
{
    context_type=$1
    context_path=$2
    if [[ ${MODE} == "install" ]] ; then
        /usr/sbin/semanage fcontext -a -t $context_type $context_path
    else
        /usr/sbin/semanage fcontext -d $context_path
    fi
}

echo "Assuming Pulp git checkout is at ${PULP_SRC_DIR}"

adjust_context "httpd_config_t" "${PULP_SRC_DIR}/etc/httpd(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/etc/httpd

adjust_context "pulp_cert_t" "${PULP_SRC_DIR}/etc/pki/pulp(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/etc/pki/pulp

adjust_context "httpd_sys_content_t" "${PULP_SRC_DIR}/etc/pulp(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/etc/pulp

adjust_context "httpd_sys_content_t" "${PULP_SRC_DIR}/srv/pulp(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/srv/pulp

adjust_context "lib_t" "${PULP_SRC_DIR}/src(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/src

adjust_context "lib_t" "${PULP_SRC_DIR}/playpen/v2_plugins(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/playpen/v2_plugins

adjust_context "lib_t" "${PULP_SRC_DIR}/plugins(/.*)?"
/sbin/restorecon -R ${PULP_SRC_DIR}/plugins


if [ -e ${PYTHON_SITE_PKGS}/gofer.egg-link ]; then
    GOFER_SRC=`head -n 1 ${PYTHON_SITE_PKGS}/gofer.egg-link`
    if [ -d ${GOFER_SRC} ]; then
        echo "Updating fcontext on ${GOFER_SRC}"
        adjust_context "lib_t" "${GOFER_SRC}(/.*)?"
        /sbin/restorecon -R ${GOFER_SRC}
    fi
fi

if [ -e ${PYTHON_SITE_PKGS}/grinder.egg-link ]; then
    GRINDER_SRC=`head -n 1 ${PYTHON_SITE_PKGS}/grinder.egg-link`
    if [ -d ${GRINDER_SRC} ]; then
        echo "Updating fcontext on ${GRINDER_SRC}"
        adjust_context "lib_t" "${GRINDER_SRC}(/.*)?"
        /sbin/restorecon -R ${GRINDER_SRC}
    fi
fi
