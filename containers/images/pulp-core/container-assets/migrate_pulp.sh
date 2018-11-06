#!/bin/bash

scl enable rh-python36 "pulp-manager migrate --noinput auth"
scl enable rh-python36 "pulp-manager migrate --noinput"
scl enable rh-python36 "pulp-manager reset-admin-password --password admin"
