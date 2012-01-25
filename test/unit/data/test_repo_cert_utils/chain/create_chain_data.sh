#!/bin/sh

export DAYS=1095
export SSL_CONF=./example_ssl.conf
export CERT_DIR=./certs
export CA_CHAIN_FILE=${CERT_DIR}/ca_chain

export ROOT_CA_DIR=${CERT_DIR}/ROOT_CA
export ROOT_CA_CERT=${ROOT_CA_DIR}/root_ca.pem
export ROOT_CA_KEY=${ROOT_CA_DIR}/root_ca_key.pem
export ROOT_CA_COMMON_NAME="Root CA Common Name"

export ROOT_CA_SSL_CONF=./root_ca_ssl.conf
export ROOT_INDEX=${ROOT_CA_DIR}/index
export ROOT_CA_SERIAL=${ROOT_CA_DIR}/serial
export ROOT_CRLNUMBER=${ROOT_CA_DIR}/crlnumber
export ROOT_CA_CRL=${ROOT_CA_DIR}/root_ca_CRL.pem

export SUB_CA_DIR=${CERT_DIR}/SUB_CA
export SUB_CA_CERT=${SUB_CA_DIR}/sub_ca.pem
export SUB_CA_KEY=${SUB_CA_DIR}/sub_ca_key.pem
export SUB_CA_COMMON_NAME="Sub CA Common Name"

export SUB_CA_CSR=${SUB_CA_DIR}/sub_ca.csr
export SUB_CA_SSL_CONF=./sub_ca_ssl.conf
export SUB_INDEX=${SUB_CA_DIR}/index
export SUB_CA_SERIAL=${SUB_CA_DIR}/serial
export SUB_CRLNUMBER=${SUB_CA_DIR}/crlnumber
export SUB_CA_CRL=${SUB_CA_DIR}/sub_ca_CRL.pem

export TEST_CERT=${CERT_DIR}/test_cert.pem
export TEST_KEY=${CERT_DIR}/test_key.pem
export TEST_CSR=${CERT_DIR}/test.csr
export TEST_COMMON_NAME="Test Common Name"

export REVOKED_CERT=${CERT_DIR}/revoked_cert.pem
export REVOKED_KEY=${CERT_DIR}/revoked_key.pem
export REVOKED_CSR=${CERT_DIR}/revoked.csr
export REVOKED_COMMON_NAME="Revoked Common Name"

if [ ! -e ${CERT_DIR} ]; then
    echo "${CERT_DIR} missing, will attempt to create directory"
    mkdir ${CERT_DIR}
fi
if [ ! -e ${ROOT_CA_DIR} ]; then
    echo "${ROOT_CA_DIR} missing, will attempt to create directory"
    mkdir ${ROOT_CA_DIR}
fi
if [ ! -e ${SUB_CA_DIR} ]; then
    echo "${SUB_CA_DIR} missing, will attempt to create directory"
    mkdir ${SUB_CA_DIR}
fi
#
# Setup CRL database info for CRL revoking
# INDEX AND CRLNUMBER need to match the setting in the
# openssl conf
#
if [ ! -e ${ROOT_INDEX} ]; then
    echo "Creating the index"
    touch ${ROOT_INDEX}
fi
if [ ! -e ${ROOT_CRLNUMBER} ]; then
    echo "Initializing ${ROOT_CRLNUMBER}"
    echo "01" > ${ROOT_CRLNUMBER}
fi
if [ ! -e ${SUB_INDEX} ]; then
    echo "Creating the index"
    touch ${SUB_INDEX}
fi
if [ ! -e ${SUB_CRLNUMBER} ]; then
    echo "Initializing ${ROOT_CRLNUMBER}"
    echo "01" > ${SUB_CRLNUMBER}
fi
#
# Create the root-CA
#
echo "Creating Root CA: ${ROOT_CA_CERT}"
openssl genrsa -out ${ROOT_CA_KEY} 2048
openssl req -new -x509 -days ${DAYS} -key ${ROOT_CA_KEY} -out ${ROOT_CA_CERT} -subj "/CN=${ROOT_CA_COMMON_NAME}"
if [ ! -e ${ROOT_CA_SERIAL} ]; then
    echo "Initializing ${ROOT_CA_SERIAL}"
    echo "01" > ${ROOT_CA_SERIAL}
fi
#
# Create the sub-CA
#
echo "Creating Sub CA: ${SUB_CA_CERT}"
openssl genrsa -out ${SUB_CA_KEY} 2048
openssl req -new -key ${SUB_CA_KEY} -out ${SUB_CA_CSR} -subj "/CN=${SUB_CA_COMMON_NAME}"
openssl x509 -req -extensions v3_ca -extfile ${SSL_CONF} -days ${DAYS} -CA ${ROOT_CA_CERT} -CAkey ${ROOT_CA_KEY} -in ${SUB_CA_CSR} -out ${SUB_CA_CERT} -CAserial ${ROOT_CA_SERIAL}
if [ ! -e ${SUB_CA_SERIAL} ]; then
    echo "Initializing ${SUB_CA_SERIAL}"
    echo "01" > ${SUB_CA_SERIAL}
fi
#
# Create a test certificate
#
echo "Creating a test cert: ${TEST_CERT}"
openssl genrsa -out ${TEST_KEY} 2048
openssl req -new -key ${TEST_KEY} -out ${TEST_CSR} -subj "/CN=${TEST_COMMON_NAME}"
openssl x509 -req -days 1095 -CA ${SUB_CA_CERT} -CAkey ${SUB_CA_KEY} -in ${TEST_CSR} -out ${TEST_CERT} -CAserial ${SUB_CA_SERIAL}
#
# Create a certificate to revoke
#
echo "Creating a cert to intentionally revoke: ${REVOKED_CERT}"
openssl genrsa -out ${REVOKED_KEY} 2048
openssl req -new -key ${REVOKED_KEY} -out ${REVOKED_CSR} -subj "/CN=${REVOKED_COMMON_NAME}"
openssl x509 -req -days 1095 -CA ${SUB_CA_CERT} -CAkey ${SUB_CA_KEY} -in ${REVOKED_CSR} -out ${REVOKED_CERT} -CAserial ${SUB_CA_SERIAL}
#
# Revoke the cert, then generate a CRL with the newly revoked info
# Remember...the location of the database to store the revoked information is configured in ${SUB_CA_SSL_CONF}
#
echo "Revoking the cert: ${REVOKED_CERT}"
openssl ca -revoke ${REVOKED_CERT} -keyfile ${SUB_CA_KEY} -cert ${SUB_CA_CERT} -config ${SUB_CA_SSL_CONF} -md sha1
openssl ca -gencrl -keyfile ${SUB_CA_KEY} -cert ${SUB_CA_CERT} -out ${SUB_CA_CRL} -config ${SUB_CA_SSL_CONF} -crlexts crl_ext -md sha1


cat ${ROOT_CA_CERT} > ${CA_CHAIN_FILE}
cat ${SUB_CA_CERT} >> ${CA_CHAIN_FILE}

