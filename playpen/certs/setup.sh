#!/bin/sh

./create_ca.py
./create_server_cert.py
./create_client_cert.py
sudo ./install.py

