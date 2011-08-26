/*
 * This is an example of using OpenSSL C APIs for verifying a X509 signature against 
 * a CA while using a CRL.
 *
 * The example is written to use the same calls Pulp plans to use with a patched version of M2Crpypto in Python
 */
#include <stdio.h>
#include <stdlib.h>
#include <openssl/x509_vfy.h>
#include <openssl/err.h>
#include <openssl/pem.h>

void handle_error(const char *file, int lineno, const char *msg)
{
    fprintf(stderr, "%s:%i %s\n", file, lineno, msg);
    ERR_print_errors_fp(stderr);
    exit(-1);
}
#define int_error(msg) handle_error(__FILE__, __LINE__, msg)

#define CA_FILE     "../certs/Pulp_CA.cert"
#define CA_DIR      "../certs/"
#define CRL_FILE    "../certs/Pulp_CRL.pem"
#define CLIENT_CERT "../certs/Pulp_client.cert"

int verify_callback(int ok, X509_STORE_CTX *stor) {
    if (!ok) {
        fprintf(stderr, "Error: %s\n", X509_verify_cert_error_string(stor->error));
    }
    return ok;
}

int main(int argc, char *argv[]) {
    X509 *cert;
    X509 *cacert;
    X509_CRL *crl;
    X509_STORE *store;
    X509_LOOKUP *lookup;
    X509_STORE_CTX *verify_ctx;
    STACK_OF(X509) *untrusted;
    STACK_OF(X509_CRL) *crls;
    FILE *fp;

    OpenSSL_add_all_algorithms();
    ERR_load_crypto_strings();

    /* read the client certificate */
    if (!(fp = fopen(CLIENT_CERT, "r"))) {
        int_error("Error reading client certificate file");
    }
    if (!(cert = PEM_read_X509(fp, NULL, NULL, NULL))) {
        int_error("Error reading client certificate in file");
    }
    fclose(fp);

    /* read CA certificate */
    if (!(fp = fopen(CA_FILE, "r"))) {
        int_error("Error reading CA certificate file");
    }
    if (!(cacert = PEM_read_X509(fp, NULL, NULL, NULL))) {
        int_error("Error reading CA certificate in file");
    }
    fclose(fp);

    // Read CRL
    if (!(fp = fopen(CRL_FILE, "r"))) {
        int_error("Error opening CRL file");
    }
    if (!(crl = PEM_read_X509_CRL(fp, NULL, NULL, NULL))) {
        int_error("Error reading CRL");
    }
    fclose(fp);
    
    /* create the cert store and set the verify callback */
    if (!(store = X509_STORE_new())) {
        int_error("Error creating X509_STORE_CTX object");
    }
    // Add CA cert to Store
    if (X509_STORE_add_cert(store, cacert) != 1) {
        int_error("Error adding CA certificate to certificate store");
    }
    // Add CRL to Store
    if (X509_STORE_add_crl(store, crl) != 1) {
        int_error("Error adding CRL to certificate store");
    }
    X509_STORE_set_verify_cb_func(store, verify_callback);
    /* set the flags of the store so that the CRLs are consulted */
    X509_STORE_set_flags(store, X509_V_FLAG_CRL_CHECK | X509_V_FLAG_CRL_CHECK_ALL);
    
    // Create an empty X509_Stack for untrusted
    if (!(untrusted = sk_X509_new_null())) {
        int_error("Error creating X509_Stack");
    }
    // Create a CRL_Stack 
    if (!(crls = sk_X509_CRL_new_null())) {
        int_error("Error creating X509_CRL");
    }
    // Add CRL to CRL_Stack
    if (sk_X509_CRL_push(crls, crl) != 1) {
        int_error("Error adding a CRL to the Stack of CRLs");
    }

    /* create a verification context and initialize it */
    if (!(verify_ctx = X509_STORE_CTX_new())) {
        int_error("Error creating X509_STORE_CTX object");
    }
    // We are explicitly adding an empty X509_Stack for untrusted
    if (X509_STORE_CTX_init(verify_ctx, store, cert, untrusted) != 1) {
        int_error("Error initializing verification context");
    }
    X509_STORE_CTX_set0_crls(verify_ctx, crls);
    /* verify the certificate */
    if (X509_verify_cert(verify_ctx) != 1) {
        int_error("Error verifying the certificate");
    }
    else {
        printf("Certificate verified correctly!\n");
    }
    return 0;
}
