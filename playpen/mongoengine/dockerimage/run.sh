#!/usr/bin/env bash

# a hacky way of waiting until mongo is done initializing itself
until echo "" | nc db 27017 2>/dev/null
do
    echo "waiting for mongodb"
    sleep 1
done

# Load user data into mongodb. The /dump/ directory should be bind-mounted into
# the container.
mongorestore --quiet --host db /dump/
if [ "$?" -ne "0" ]; then
    echo ""
    echo "Could not read dump directory."
    echo "If selinux in enforcing, consider: chcon -Rt svirt_sandbox_file_t dump"
    echo ""
    exit 1
fi

# supress warnings from mongoengine
export PYTHONWARNINGS="ignore"

python /validation_check.py

