# Regenerating these certificates

To regenerate the signed certificates in this directory in order to update their expiration dates,
run the regenerate.sh script in this directory.

The repoauth package has a few SSL-related tests, so rather than repeat all of these steps in that
dir, regenerate.sh copies the newly created cert.crt and valid_ca.crt over to repoauth/test/data
if that directory is in the expected location relative to this one (as with a git clone). Since the
repoauth certs are copies of the certs generated here, it's very likely that whatever problem
requires the certs to be regenerated affects both oid_validation and repoauth, so the certs are
updated in both places.


# Background Information

The pulp_ssl.cnf file is a configuration file created just for these certificates, which pre-
configures openssl for creating and signing the certificates in this dir. That config file is
then used by regenerate.sh to ensure that openssl's behavior is predictable and repeatable.

## What regenerate.sh specifics

It creates two basic trust chains of a CA and a cert signed by that CA. A "valid" CA is created, and
an "other" CA is created. Then, it creates certificates signed by both of the authorities to create
testable scenarios, such as making sure a certificate is accepted when Pulp requires a cert
signed by the valid CA, or making sure a certificate is rejected when Pulp requires a cert signed
by the other CA, etc. The only thing that makes the "valid" CA more valid, when compared to the "other"
CA, is how it is used in testing.

Both the valid and other CA certificates are self-signed.

The `-subj` flag to openssl is used extensively to me various certs easy to distinguish from one
another.

Different types of entitlement certificates are then created, all signed by the "valid" CA, each
representing a different scenario that may be seen in a "real" entitelement client cert.

The `-config pulp_ssl.cnf` and `-batch` options passed to `openssl req` make it so you don't have
to fill in any fields to make a certificate or signing request, which makes regenerate.sh work
without requiring user interaction. The `-nodes` flag prevents user interaction as well, and also
stop openssl from encrypting any keys using a passphrase, which we want since these are certificates
used only for testing functionality.

When generating the signed certificate with `openssl x509`, it again points to `pulp_ssl.cnf` using
the `-extfile` options, but tell openssql to load SSLv3 extensions explicitly from the `usr_cert`
section of our config with `-extfile` and `-extensions`, and then use `-clrext` to tell openssl
to ignore any extensions that might be attached to the signing request, ensuring the certificate
is made exactly as expected for our testing purposes, and very much like "real" certificates would
be created in a production setting.

To update the values used in the generated subjectAltName fields, add to the `alt_names` section of
`pulp_ssl.cnf`.
