#!/bin/sh
export CERT_DIR=./certs
export CA_CHAIN_FILE=${CERT_DIR}/ca_chain

export ROOT_CA_DIR=${CERT_DIR}/ROOT_CA
export ROOT_CA_CERT=${ROOT_CA_DIR}/root_ca.pem
export SUB_CA_DIR=${CERT_DIR}/SUB_CA
export SUB_CA_CERT=${SUB_CA_DIR}/sub_ca.pem

export TEST_CERT=${CERT_DIR}/test_cert.pem


if [ ! -e ${CA_CHAIN_FILE} ]; then
    echo "Create the CA certificate chain: ${CA_CHAIN_FILE}"
    cat ${ROOT_CA_CERT} > ${CA_CHAIN_FILE}
    cat ${SUB_CA_CERT} >> ${CA_CHAIN_FILE}
fi

openssl verify -CAfile ${CA_CHAIN_FILE} ${TEST_CERT}

