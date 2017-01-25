#!/bin/bash -ex

create_and_sign() {
	certname=$1
    authority=$2
    extensions=$3

	# create the cert signing request
	openssl req -newkey rsa:4096 -keyout ${certname}.key -out ${certname}.req -nodes -config pulp_ssl.cnf \
        -subj /CN=${certname}/ -batch
	# sign the cert
	openssl x509 -req -in ${certname}.req -signkey ${certname}.key -CA ${authority}.crt -CAkey ${authority}.key \
	  -CAcreateserial -days 3650 -extfile pulp_ssl.cnf -extensions ${extensions} -clrext -text > ${certname}.crt
	# clean up the CSR
	rm ${certname}.req
	# clean up the generated CA serial
	rm ${authority}.srl
}

# regenerate the "valid" ceriticate authority
# this will sign most of the certs generated here
openssl req -x509 -newkey rsa:4096 -keyout valid_ca.key -out valid_ca.crt -days 3650 -nodes \
  -config pulp_ssl.cnf -subj /CN=pulp-ca/ -extensions ca_cert -batch

# regenerate the "other" CA
# this will sign other certs, useful in testing that certs signed by an untrusted authority
# are rejected, for example
openssl req -x509 -newkey rsa:4096 -keyout other_ca.key -out other_ca.crt -days 3650 -nodes \
  -config pulp_ssl.cnf -subj /CN=pulp-other-ca/ -extensions ca_cert -batch

# create a certificate signing request for pulp-server and sign with the valid ca
create_and_sign cert valid_ca usr_cert

# create and sign a certificate with the "other" CA
create_and_sign other_cert other_ca usr_cert

# create and sign a few different entitlement certs
create_and_sign e_limited valid_ca limited_entitlement
create_and_sign e_full valid_ca full_entitlement
create_and_sign e_variable valid_ca variable_entitlement
create_and_sign e_wildcard valid_ca wildcard_entitlement

# if the repoauth data dir exists and all the cert regeneration commands succeeded,
# copy some of the regenerated files there so it can also benefit from cert regeneration
repoauth_data="$(dirname $0)/../../../repoauth/test/data"
if [ -d $repoauth_data ]
then
    cp valid_ca.crt cert.crt $repoauth_data
fi
