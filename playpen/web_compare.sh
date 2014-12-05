#!/bin/bash

rm /tmp/django.headers
rm /tmp/webpy.headers

rm /tmp/django.body
rm /tmp/webpy.body

rm /tmp/django.json
rm /tmp/webpy.json

curl -I -H "Accept: application/json" -H "WebFrameworkSwitch: django" -X $1 -k -u admin:admin -o /tmp/django.headers "https://localhost/pulp/api$2"
curl -I -H "Accept: application/json" -H "WebFrameworkSwitch: webpy" -X $1 -k -u admin:admin -o /tmp/webpy.headers "https://localhost/pulp/api$2"

curl -H "Accept: application/json" -H "WebFrameworkSwitch: django" -X $1 -k -u admin:admin -o /tmp/django.body "https://localhost/pulp/api$2"
curl -H "Accept: application/json" -H "WebFrameworkSwitch: webpy" -X $1 -k -u admin:admin -o /tmp/webpy.body "https://localhost/pulp/api$2"

python -mjson.tool /tmp/webpy.body > /tmp/webpy.json
python -mjson.tool /tmp/django.body > /tmp/django.json

if [ -n "$3" ]
  then
    vimdiff /tmp/webpy.headers /tmp/django.headers
fi;

vimdiff /tmp/webpy.json /tmp/django.json
