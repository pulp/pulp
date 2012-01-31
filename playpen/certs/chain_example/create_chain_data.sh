#!/bin/sh

export DAYS=1095
export EXT_FILE=./extensions.txt
export SSL_CONF=./example_ssl.conf
export CERT_DIR=./certs
export CA_CHAIN_FILE=${CERT_DIR}/ca_chain
export ROOT_CA_DIR=${CERT_DIR}/ROOT_CA
export ROOT_CA_CERT=${ROOT_CA_DIR}/root_ca.pem
export ROOT_CA_KEY=${ROOT_CA_DIR}/root_ca_key.pem
export ROOT_CA_SERIAL=${ROOT_CA_DIR}/root_ca_serial
export ROOT_CA_COMMON_NAME="Root CA Common Name"
export ROOT_CA_SERIAL=${ROOT_CA_DIR}/serial

export SUB_CA_DIR=${CERT_DIR}/SUB_CA
export SUB_CA_CERT=${SUB_CA_DIR}/sub_ca.pem
export SUB_CA_KEY=${SUB_CA_DIR}/sub_ca_key.pem
export SUB_CA_SERIAL=${SUB_CA_DIR}/sub_ca_serial
export SUB_CA_CSR=${SUB_CA_DIR}/sub_ca.csr
export SUB_CA_SERIAL=${SUB_CA_DIR}/serial
export SUB_CA_COMMON_NAME="Sub CA Common Name"

export TEST_CERT=${CERT_DIR}/test_cert.pem
export TEST_KEY=${CERT_DIR}/test_key.pem
export TEST_CSR=${CERT_DIR}/test.csr
export TEST_COMMON_NAME="Test Common Name"

# INDEX AND CRLNUMBER need to match the setting in the
# openssl conf
INDEX=${CERT_DIR}/index
CRLNUMBER=${CERT_DIR}/crlnumber
CONF_FILE=./revoking_ssl.conf
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
openssl x509 -req -days 1095 -CA ${SUB_CA_CERT} -CAkey ${SUB_CA_KEY} -extfile ${EXT_FILE} -extensions pulp-repos -in ${TEST_CSR} -out ${TEST_CERT} -CAserial ${SUB_CA_SERIAL}

cat ${ROOT_CA_CERT} > ${CA_CHAIN_FILE}
cat ${SUB_CA_CERT} >> ${CA_CHAIN_FILE}

