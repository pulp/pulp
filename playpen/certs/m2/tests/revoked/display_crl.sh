export CERT_DIR=./certs
if [ $# -lt 1 ]; then
    export CRL_FILE=${CERT_DIR}/revoking_crl.pem
    echo "Defaulting to look at CRL: ${CRL_FILE}"
else
    export CRL_FILE=$1
fi

openssl crl -text -in ${CRL_FILE} -noout
