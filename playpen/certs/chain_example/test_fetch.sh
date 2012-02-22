export CERT_DIR=./certs
export CA_CERT=${CERT_DIR}/SUB_CA/sub_ca.pem
export CA_CHAIN_FILE=${CERT_DIR}/ca_chain
export TEST_CERT=${CERT_DIR}/test_cert.pem
export TEST_KEY=${CERT_DIR}/test_key.pem

#pulp-admin repo create --id pulp_f15_x86_64 --feed http://repos.fedorapeople.org/repos/pulp/pulp/v1/testing/fedora-15/x86_64/ --consumer_ca ${CA_CHAIN_FILE} --consumer_cert ${TEST_CERT} --consumer_key ${TEST_KEY}

#pulp-admin repo sync --id pulp_f15_x86_64 -F

curl -k --cert ${TEST_CERT} --key ${TEST_KEY}  https://`hostname`/pulp/repos/repos/pulp/pulp/v1/testing/fedora-15/x86_64/repodata/repomd.xml
#wget --no-check-certificate --certificate ${TEST_CERT} --private-key ${TEST_KEY} https://`hostname`/pulp/repos/repos/pulp/pulp/fedora-15/x86_64/repodata/repomd.xml

