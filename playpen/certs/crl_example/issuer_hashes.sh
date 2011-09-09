echo "CA hash            `openssl x509 -issuer_hash -in ./certs/Pulp_CA.cert -noout`"
echo "CRL hash:          `openssl crl -in ./certs/Pulp_CRL.pem -hash -noout`"
echo "Good cert hash:    `openssl x509 -issuer_hash -in ./ok/Pulp_client.cert -noout`"
echo "Revoked cert hash: `openssl x509 -issuer_hash -in ./revoked/Pulp_client.cert -noout`"
