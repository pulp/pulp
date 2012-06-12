CERT_DIR=./
CA_KEY=${CERT_DIR}/Pulp_CA.key
CA_CERT=${CERT_DIR}/Pulp_CA.cert
CRL_FILE=${CERT_DIR}/Pulp_CRL.pem
SSL_CONF=${CERT_DIR}/openssl_crl.cnf

openssl ca -gencrl -keyfile ${CA_KEY} -cert ${CA_CERT} -out ${CRL_FILE} -config ${SSL_CONF} -crlexts crl_ext -md sha1


