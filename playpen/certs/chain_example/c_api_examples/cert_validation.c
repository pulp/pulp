#include <stdio.h>
#include <stdlib.h>
#include <openssl/x509_vfy.h>
#include <openssl/err.h>
#include <openssl/pem.h>
/**
 * This file serves as a test to see how we can load a certificate chain with the 
 * APIs.
 *
 * Refer to openssl C source:  crypto/x509/x509_d2.c to see the definition
 * for:  X509_STORE_load_locations()
 * 
*/

void handle_error(const char *file, int lineno, const char *msg)
{
    fprintf(stderr, "%s:%i %s\n", file, lineno, msg);
    ERR_print_errors_fp(stderr);
    exit(-1);
}
#define int_error(msg) handle_error(__FILE__, __LINE__, msg)

#define CA_CERT_CHAIN "../certs/ca_chain"
#define CA_DIR      "../certs/"
#define TEST_CERT "../certs/test_cert.pem"

int verify_callback(int ok, X509_STORE_CTX *stor) {
    if (!ok) {
        fprintf(stderr, "Error: %s\n", X509_verify_cert_error_string(stor->error));
    }
    return ok;
}

int main(int argc, char *argv[]) {
    X509 *cert;
    X509_STORE *store;
    X509_LOOKUP *lookup;
    X509_STORE_CTX *verify_ctx;
    FILE *fp;

    OpenSSL_add_all_algorithms();
    ERR_load_crypto_strings();

    /* frist read the client certificate */
    if (!(fp = fopen(TEST_CERT, "r"))) {
        int_error("Error reading client certificate file");
    }
    if (!(cert = PEM_read_X509(fp, NULL, NULL, NULL))) {
        int_error("Error reading client certificate in file");
    }
    fclose(fp);

    /* create the cert store and set the verify callback */
    if (!(store = X509_STORE_new())) {
        int_error("Error creating X509_STORE_CTX object");
    }
    X509_STORE_set_verify_cb_func(store, verify_callback);

    /* load the CA certificates and CRLs */
    if (X509_STORE_load_locations(store, CA_CERT_CHAIN, CA_DIR) != 1) {
        int_error("Error loading the CA file or directory");
    }
    if (X509_STORE_set_default_paths(store) != 1) {
        int_error("Error loading the system-wide CA certificates");
    }
    /* create a verification context and initialize it */
    if (!(verify_ctx = X509_STORE_CTX_new())) {
        int_error("Error creating X509_STORE_CTX object");
    }
    if (X509_STORE_CTX_init(verify_ctx, store, cert, NULL) != 1) {
        int_error("Error initializing verification context");
    }
    /* verify the certificate */
    if (X509_verify_cert(verify_ctx) != 1) {
        int_error("Error verifying the certificate");
    }
    else {
        printf("Certificate verified correctly!\n");
    }
    return 0;
}



