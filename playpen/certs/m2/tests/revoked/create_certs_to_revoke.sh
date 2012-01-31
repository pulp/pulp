#!/bin/sh

export CERT_DIR=./certs
export VALID_KEY=${CERT_DIR}/valid_key.pem
export VALID_CERT=${CERT_DIR}/valid_cert.pem
export VALID_CSR=${CERT_DIR}/valid_csr
export REVOKED_KEY=${CERT_DIR}/revoked_key.pem
export REVOKED_CERT=${CERT_DIR}/revoked_cert.pem
export REVOKED_CSR=${CERT_DIR}/revoked_csr
export CA_CERT=${CERT_DIR}/revoking_ca.pem
export CA_KEY=${CERT_DIR}/revoking_ca_key.pem
export CA_SERIAL=${CERT_DIR}/revoking_ca_serial
export CRL_FILE=${CERT_DIR}/revoking_crl.pem
export CA_COMMON_NAME="CA_SIGNER"
export CLIENT_COMMON_NAME="CLIENT"
# INDEX AND CRLNUMBER need to match the setting in the
# openssl conf
INDEX=${CERT_DIR}/index
CRLNUMBER=${CERT_DIR}/crlnumber
CONF_FILE=./revoking_ssl.conf
if [ ! -e ${CERT_DIR} ]; then
    echo "${CERT_DIR} missing, will attempt to create directory"
    mkdir ${CERT_DIR}
fi
#
# Create the CA
#
echo "Creating a test CA"
openssl genrsa -out ${CA_KEY} 2048
openssl req -new -x509 -days 1095 -key ${CA_KEY} -out ${CA_CERT} -subj "/CN=${CA_COMMON_NAME}"
if [ ! -e ${CA_SERIAL} ]; then
    echo "Initializing ${CA_SERIAL}"
    echo "01" > ${CA_SERIAL}
fi
# 
# Create a valid cert that will _not_ be revoked
#
echo "Creating a test cert that will remain valid: ${VALID_CERT}"
openssl genrsa -out ${VALID_KEY} 2048
openssl req -new -key ${VALID_KEY} -out ${VALID_CSR} -subj "/CN=${CLIENT_COMMON_NAME}"
openssl x509 -req -days 1095 -CA ${CA_CERT} -CAkey ${CA_KEY} -in ${VALID_CSR} -out ${VALID_CERT} -CAserial ${CA_SERIAL}


#
# Create a test cert so we can revoke it later
#
echo "Creating a test cert to revoke in later step: ${REVOKED_CERT}"
openssl genrsa -out ${REVOKED_KEY} 2048
openssl req -new -key ${REVOKED_KEY} -out ${REVOKED_CSR} -subj "/CN=${CLIENT_COMMON_NAME}"
openssl x509 -req -days 1095 -CA ${CA_CERT} -CAkey ${CA_KEY} -in ${REVOKED_CSR} -out ${REVOKED_CERT} -CAserial ${CA_SERIAL}
#
# Setup CRL database info for CRL revoking
#
if [ ! -e ${INDEX} ]; then
    echo "Creating the index"
    touch ${INDEX}
fi
if [ ! -e ${CRLNUMBER} ]; then
    echo "Initializing ${CRLNUMBER}"
    echo "01" > ${CRLNUMBER}
fi
#
# Revoke the cert, then generate a CRL with the newly revoked info
#
echo "Revoking the cert: ${REVOKED_CERT}"
openssl ca -revoke ${REVOKED_CERT} -keyfile ${CA_KEY} -cert ${CA_CERT} -config ${CONF_FILE} -md sha1
openssl ca -gencrl -keyfile ${CA_KEY} -cert ${CA_CERT} -out ${CRL_FILE} -config ${CONF_FILE} -crlexts crl_ext -md sha1
