CC=gcc
CFLAGS=-g -Wall
LIBS=-lpthread -lssl -lcrypto


all: cert_validation cert_validation_B

cert_validation: cert_validation.c
	$(CC) -o cert_validation cert_validation.c -I $(INCLUDE) $(LIBS)

cert_validation_B: cert_validation_B.c
	$(CC) -o cert_validation_B cert_validation_B.c -I $(INCLUDE) $(LIBS)

clean:
	-rm cert_validation cert_validation_B

