#!/bin/bash -x

echo "$QUAY_PASSWORD" | docker login -u "$QUAY_LOGIN" --password-stdin quay.io

cd containers

ansible-playbook build.yaml -e tag=$VERSION
ansible-playbook push.yaml -e tag=$VERSION
